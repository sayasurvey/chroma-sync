import os
from pathlib import Path

import numpy as np
from wand.image import Image

from app.converter.color_diff import ColorDiffCalculator
from app.converter.color_profile import ColorProfileManager
from app.converter.llm_advisor import LLMColorAdvisor
from app.models.job import ConversionJob, ConversionOptions
from app.models.result import ConversionResult, Region

# 定数
DEFAULT_QUALITY = 85
MAX_DELTA_E = 2.0
MAX_CORRECTION_ATTEMPTS = 3


class ConversionEngine:
    """AI/PSDファイルをJPEGに変換するメインエンジン。

    ImageMagick (Wand) と lcms2 を使用してカラープロファイルを保持しながら変換します。
    変換後の色差（ΔE）を計算し、閾値を超えた場合は自動色補正を適用します。
    """

    def __init__(self) -> None:
        self._profile_manager = ColorProfileManager()
        self._diff_calculator = ColorDiffCalculator()
        self._llm_advisor = LLMColorAdvisor()

    def convert(
        self,
        input_path: str,
        output_path: str,
        options: ConversionOptions,
        job: ConversionJob | None = None,
    ) -> ConversionResult:
        """AI/PSDファイルをJPEGに変換する。

        Args:
            input_path: 入力ファイルのパス（.ai または .psd）
            output_path: 出力JPEGのパス
            options: 変換オプション
            job: 進捗更新用のジョブオブジェクト（オプション）

        Returns:
            変換結果
        """
        original_size = os.path.getsize(input_path)
        self._update_progress(job, 10, "カラープロファイルを読み取り中...")

        # ICCカラープロファイルを取得
        source_profile = self._profile_manager.get_icc_profile(input_path)

        self._update_progress(job, 20, "画像を変換中...")

        # 変換とsRGB変換
        temp_output = output_path + ".tmp.jpg"
        self._convert_to_jpeg(input_path, temp_output, options, source_profile)

        self._update_progress(job, 50, "色差を計算中...")

        # 色差計算（元ファイルをPNGで比較用に出力）
        reference_path = output_path + ".ref.png"
        self._export_reference(input_path, reference_path, source_profile)

        delta_e = self._diff_calculator.calculate_delta_e(reference_path, temp_output)

        corrections_applied = False
        correction_regions: list[Region] = []

        if delta_e > options.max_delta_e:
            self._update_progress(job, 60, f"色ずれを検出 (ΔE={delta_e:.2f})。自動修正中...")
            regions = self._diff_calculator.get_diff_regions(
                reference_path, temp_output, options.max_delta_e
            )

            for attempt in range(MAX_CORRECTION_ATTEMPTS):
                self._update_progress(
                    job, 60 + attempt * 10, f"色補正試行 {attempt + 1}/{MAX_CORRECTION_ATTEMPTS}..."
                )

                self._apply_color_correction(reference_path, temp_output)
                delta_e = self._diff_calculator.calculate_delta_e(reference_path, temp_output)
                corrections_applied = True

                if delta_e <= options.max_delta_e:
                    break

            # LLM補正を試みる
            if delta_e > options.max_delta_e and options.use_llm:
                self._update_progress(job, 90, "LLMによる高度な色補正を試みています...")
                plan = self._llm_advisor.suggest_color_correction(
                    reference_path, temp_output, regions
                )
                if plan:
                    self._llm_advisor.apply_llm_correction(temp_output, plan)
                    delta_e = self._diff_calculator.calculate_delta_e(reference_path, temp_output)

            # 補正後のΔEを更新
            for region in regions:
                region.delta_e_after = delta_e
            correction_regions = regions

        # 目標サイズに合わせる
        if options.target_size_kb:
            self._update_progress(job, 92, "ファイルサイズを調整中...")
            self._adjust_to_target_size(temp_output, output_path, options.target_size_kb)
        else:
            os.rename(temp_output, output_path)

        # 一時ファイルの削除
        for tmp in [reference_path, temp_output]:
            if os.path.exists(tmp):
                os.unlink(tmp)

        output_size = os.path.getsize(output_path)

        return ConversionResult(
            job_id=getattr(job, "job_id", ""),
            success=True,
            output_path=output_path,
            original_size_bytes=original_size,
            output_size_bytes=output_size,
            delta_e=delta_e,
            corrections_applied=corrections_applied,
            correction_regions=correction_regions,
        )

    def _convert_to_jpeg(
        self,
        input_path: str,
        output_path: str,
        options: ConversionOptions,
        source_profile: bytes | None,
    ) -> None:
        """ファイルをJPEGに変換する。

        Args:
            input_path: 入力ファイルのパス
            output_path: 出力JPEGのパス
            options: 変換オプション
            source_profile: ICCプロファイル
        """
        with Image(resolution=300) as img:
            # AI/PDF ファイルは Ghostscript 経由で高解像度レンダリング
            img.read(filename=self._get_wand_filename(input_path))

            # 最初のフレームのみ使用（複数ページのPSD/AIの場合）
            if len(img.sequence) > 1:
                with img.sequence[0] as frame:
                    single = Image(image=frame)
                img.close()
                img = single

            # sRGBへのカラープロファイル変換
            img = self._profile_manager.convert_to_srgb(img, source_profile)

            # JPEG設定
            img.format = "jpeg"
            img.compression_quality = options.quality

            img.save(filename=output_path)

    def _export_reference(
        self, input_path: str, reference_path: str, source_profile: bytes | None
    ) -> None:
        """比較用のリファレンス画像をPNGとして出力する。

        PNG形式で出力することで色空間変換なしの参照画像を作成します。

        Args:
            input_path: 入力ファイルのパス
            reference_path: リファレンス画像の出力パス
            source_profile: ICCプロファイル
        """
        with Image(resolution=300) as img:
            img.read(filename=self._get_wand_filename(input_path))

            if len(img.sequence) > 1:
                with img.sequence[0] as frame:
                    single = Image(image=frame)
                img.close()
                img = single

            img = self._profile_manager.convert_to_srgb(img, source_profile)
            img.format = "png"
            img.save(filename=reference_path)

    def _apply_color_correction(self, reference_path: str, target_path: str) -> None:
        """色差マップに基づいて色補正を適用する。

        参照画像との平均色差を計算し、ガンマ補正とレベル調整で
        色味を参照画像に近づけます。

        Args:
            reference_path: 参照画像のパス
            target_path: 補正対象のJPEGパス（インプレースで修正）
        """
        import skimage.io as sk_io
        from skimage import color as sk_color
        from skimage.transform import resize

        ref_img = sk_io.imread(reference_path).astype(float) / 255.0
        tgt_img = sk_io.imread(target_path).astype(float) / 255.0

        # サイズを合わせる
        if ref_img.shape != tgt_img.shape:
            ref_img = resize(ref_img, tgt_img.shape[:2], anti_aliasing=True)

        # アルファチャンネルを除去
        if ref_img.shape[-1] == 4:
            ref_img = ref_img[..., :3]
        if tgt_img.shape[-1] == 4:
            tgt_img = tgt_img[..., :3]

        # Lab空間での平均シフト補正
        ref_lab = sk_color.rgb2lab(ref_img)
        tgt_lab = sk_color.rgb2lab(tgt_img)

        # チャンネルごとの平均差分を補正
        for c in range(3):
            diff = np.mean(ref_lab[..., c]) - np.mean(tgt_lab[..., c])
            tgt_lab[..., c] = np.clip(tgt_lab[..., c] + diff, -128, 128)

        # Lab空間でのL成分クリッピング
        tgt_lab[..., 0] = np.clip(tgt_lab[..., 0], 0, 100)

        # RGB空間に戻す
        corrected_rgb = sk_color.lab2rgb(tgt_lab)
        corrected_uint8 = (corrected_rgb * 255).astype(np.uint8)

        sk_io.imsave(target_path, corrected_uint8, quality=95)

    def _adjust_to_target_size(
        self, input_path: str, output_path: str, target_size_kb: int
    ) -> None:
        """目標ファイルサイズになるようにJPEG品質を調整する。

        二分探索で最適な品質値を見つけます。

        Args:
            input_path: 入力JPEGのパス
            output_path: 出力JPEGのパス
            target_size_kb: 目標ファイルサイズ（KB）
        """
        target_bytes = target_size_kb * 1024
        lo, hi = 10, 95

        with Image(filename=input_path) as img:
            img.format = "jpeg"

            # 二分探索で適切な品質を見つける
            for _ in range(8):
                mid = (lo + hi) // 2
                img.compression_quality = mid

                import io

                buffer = io.BytesIO()
                img.save(file=buffer)
                size = buffer.tell()

                if size <= target_bytes:
                    lo = mid
                else:
                    hi = mid - 1

                if lo >= hi:
                    break

            img.compression_quality = lo
            img.save(filename=output_path)

    @staticmethod
    def _get_wand_filename(input_path: str) -> str:
        """AI/PSD ファイルを正しく読み込むための Wand ファイル名を返す。

        AI ファイル（PDF ベース）は Ghostscript を通じて処理するため
        pdf: プレフィックスを付け、最初のページのみを対象にします。

        Args:
            input_path: 入力ファイルのパス

        Returns:
            Wand で使用するファイル名
        """
        ext = Path(input_path).suffix.lower()
        if ext == ".ai":
            # AI ファイルは PDF ベースのため pdf: プレフィックスで最初のページを読む
            return f"pdf:{input_path}[0]"
        return input_path

    @staticmethod
    def _update_progress(
        job: ConversionJob | None, progress: int, message: str
    ) -> None:
        """ジョブの進捗を更新する。

        Args:
            job: 更新するジョブ（Noneの場合は何もしない）
            progress: 進捗率 (0-100)
            message: 進捗メッセージ
        """
        if job is not None:
            job.progress = progress
            job.progress_message = message
