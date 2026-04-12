import os
import subprocess
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

    def _render_psd_via_imagemagick(self, input_path: str, output_path: str) -> bool:
        """ImageMagick CLI を直接呼び出して PSD を sRGB JPEG に変換する。

        PSD に埋め込まれた CMYK ICC プロファイルをそのまま変換元として使用し、
        sRGB へ直接変換する。+profile * で埋め込みプロファイルを削除すると
        誤ったソースプロファイルが適用されて色ずれが発生するため、
        埋め込みプロファイルが存在する場合は保持して変換する。

        Args:
            input_path: PSD ファイルのパス
            output_path: 出力 JPEG のパス

        Returns:
            成功した場合 True
        """
        srgb_path = self._profile_manager._find_profile(ColorProfileManager.SRGB_PROFILE_PATHS)
        if not srgb_path:
            return False

        # PSD に埋め込みプロファイルがあるかチェック
        source_profile = self._profile_manager.get_icc_profile(input_path)
        has_embedded_profile = source_profile is not None and len(source_profile) > 4

        cmd = [
            "convert",
            "-density", "300",
            f"{input_path}[0]",
        ]

        if not has_embedded_profile:
            # 埋め込みプロファイルがない場合のみデフォルト CMYK プロファイルを割り当て
            # （ImageMagick に変換元の色空間を伝えるため）
            cmyk_path = self._profile_manager._find_profile(ColorProfileManager.CMYK_PROFILE_PATHS)
            if cmyk_path:
                cmd += ["-profile", cmyk_path]

        # 埋め込みプロファイル（または割り当てたプロファイル）から sRGB へ変換
        # -intent Perceptual + 黒点補正で視覚的に正確な色変換を行う
        cmd += [
            "-intent", "Perceptual",
            "-black-point-compensation",
            "-profile", srgb_path,
            "-quality", "92",
            output_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0 and Path(output_path).exists()
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def _render_ai_via_ghostscript(self, input_path: str, output_path: str) -> bool:
        """Ghostscript を直接呼び出して AI ファイルを sRGB PNG にレンダリングする。

        ImageMagick 経由の Ghostscript 呼び出しでは ICC カラーマネジメントが
        正しく適用されないため、直接 Ghostscript を起動して -dUseCIEColor と
        ICC プロファイルを明示的に指定することで正確な色再現を行う。

        P3 出力は廃止: GS が P3 PNG を出力した後 Wand で P3→sRGB 変換を行う
        2段階変換が色ずれの原因となるため、GS で直接 sRGB に変換する。

        Args:
            input_path: AI ファイルのパス
            output_path: 出力 PNG のパス

        Returns:
            成功した場合 True
        """
        # sRGB のみ使用（P3→sRGB の2段階変換で色ずれが発生するため P3 は廃止）
        output_profile_path = self._profile_manager._find_profile(ColorProfileManager.SRGB_PROFILE_PATHS)
        cmyk_path = self._profile_manager._find_profile(ColorProfileManager.CMYK_PROFILE_PATHS)

        cmd = [
            "gs",
            "-dBATCH", "-dNOPAUSE", "-dQUIET",
            "-sDEVICE=png16m",
            "-r300",
            "-dFirstPage=1", "-dLastPage=1",
            "-dUseCIEColor",
        ]

        # 出力プロファイルを指定（sRGB のみ）
        if output_profile_path:
            cmd.append(f"-sOutputICCProfile={output_profile_path}")

        # デフォルト CMYK プロファイルを指定（未タグ CMYK コンテンツ用）
        if cmyk_path:
            cmd.append(f"-sDefaultCMYKProfile={cmyk_path}")

        cmd.append(f"-sOutputFile={output_path}")
        cmd.append(input_path)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0 and Path(output_path).exists()
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def _render_psd_to_png(self, input_path: str, output_path: str) -> bool:
        """ImageMagick CLI を使って PSD を sRGB PNG として出力する。

        比較用リファレンス画像の生成に使用。JPEG 中間ファイルを経由せず
        PNG（可逆）で直接出力することで色の劣化を防ぐ。
        _render_psd_via_imagemagick と同じプロファイル保持ロジックを使用する。

        Args:
            input_path: PSD ファイルのパス
            output_path: 出力 PNG のパス

        Returns:
            成功した場合 True
        """
        srgb_path = self._profile_manager._find_profile(ColorProfileManager.SRGB_PROFILE_PATHS)
        if not srgb_path:
            return False

        source_profile = self._profile_manager.get_icc_profile(input_path)
        has_embedded_profile = source_profile is not None and len(source_profile) > 4

        cmd = [
            "convert",
            "-density", "300",
            f"{input_path}[0]",
        ]

        if not has_embedded_profile:
            cmyk_path = self._profile_manager._find_profile(ColorProfileManager.CMYK_PROFILE_PATHS)
            if cmyk_path:
                cmd += ["-profile", cmyk_path]

        cmd += [
            "-intent", "Perceptual",
            "-black-point-compensation",
            "-profile", srgb_path,
            output_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0 and Path(output_path).exists()
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def _convert_to_jpeg(
        self,
        input_path: str,
        output_path: str,
        options: ConversionOptions,
        source_profile: bytes | None,
    ) -> None:
        """ファイルをJPEGに変換する。

        AI ファイルは Ghostscript を直接呼び出して ICC カラーマネジメント付きで
        レンダリングし、その PNG を JPEG に変換します。
        PSD など AI 以外のファイルは Wand による変換を行います。

        Args:
            input_path: 入力ファイルのパス
            output_path: 出力JPEGのパス
            options: 変換オプション
            source_profile: ICCプロファイル
        """
        ext = Path(input_path).suffix.lower()

        if ext == ".ai":
            # Ghostscript で sRGB 直接レンダリング → PNG → JPEG
            # GS が sRGB ICC プロファイルで出力するため追加の色変換は不要
            png_tmp = output_path + ".gs_tmp.png"
            try:
                if self._render_ai_via_ghostscript(input_path, png_tmp):
                    with Image(filename=png_tmp) as img:
                        # Ghostscript が sRGB で直接出力済み → 2次変換は行わない
                        img.format = "jpeg"
                        img.compression_quality = options.quality
                        img.save(filename=output_path)
                    return  # 成功時はここで終了（finally で png_tmp を削除）
            finally:
                if Path(png_tmp).exists():
                    os.unlink(png_tmp)
            # Ghostscript 失敗時はフォールバックとして Wand 変換を続行

        if ext == ".psd":
            # ImageMagick CLI で ICC 色管理付き変換
            # Wand Python の profile 割り当ては CMYK 画像で正しく動作しないため CLI を使用
            tmp_jpg = output_path + ".im_tmp.jpg"
            try:
                if self._render_psd_via_imagemagick(input_path, tmp_jpg):
                    # 品質調整: CLI は品質 92 で出力済み → 必要なら Wand で再エンコード
                    if options.quality != 92:
                        with Image(filename=tmp_jpg) as img:
                            img.format = "jpeg"
                            img.compression_quality = options.quality
                            img.save(filename=output_path)
                    else:
                        os.rename(tmp_jpg, output_path)
                    return
            finally:
                if Path(tmp_jpg).exists():
                    os.unlink(tmp_jpg)
            # ImageMagick CLI 失敗時はフォールバック

        # フォールバック: Wand による変換（RGB ファイルまたは CLI 失敗時）
        with Image(resolution=300) as img:
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

        AI ファイルは Ghostscript で ICC 色管理付きレンダリングを行い、
        正確な色を持つリファレンス画像を生成します。

        Args:
            input_path: 入力ファイルのパス
            reference_path: リファレンス画像の出力パス
            source_profile: ICCプロファイル
        """
        ext = Path(input_path).suffix.lower()

        if ext == ".ai":
            if self._render_ai_via_ghostscript(input_path, reference_path):
                return  # GS で直接 PNG として保存完了
            # Ghostscript 失敗時はフォールバック

        if ext == ".psd":
            # ImageMagick CLI で sRGB PNG として直接出力（JPEG 中間ファイルなし）
            if self._render_psd_to_png(input_path, reference_path):
                return
            # CLI 失敗時はフォールバック

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

        参照画像との平均色差を計算し、Lab空間での平均シフトで
        色味を参照画像に近づけます。
        補正後は Wand で sRGB ICC プロファイルを埋め込んで保存します。

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

        # Wand で保存して sRGB ICC プロファイルを埋め込む
        # sk_io.imsave はプロファイルを削除するため使用しない
        srgb_path = self._profile_manager._find_profile(ColorProfileManager.SRGB_PROFILE_PATHS)
        with Image.from_array(corrected_uint8) as img:
            if srgb_path:
                with open(srgb_path, "rb") as f:
                    img.profiles["icc"] = f.read()
            img.format = "jpeg"
            img.compression_quality = 95
            img.save(filename=target_path)

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
