from pathlib import Path

from wand.image import Image


class ColorProfileManager:
    """ICCカラープロファイルの読み取りとsRGBへの変換を管理するクラス"""

    # sRGB ICCプロファイルのパス（ImageMagickにバンドルされているもの）
    SRGB_PROFILE_PATH = "/usr/share/color/icc/colord/sRGB.icc"
    SRGB_PROFILE_PATH_ALT = "/usr/share/ghostscript/icc/default_rgb.icc"

    def get_icc_profile(self, file_path: str) -> bytes | None:
        """ファイルからICCカラープロファイルを取得する。

        Args:
            file_path: 画像ファイルのパス

        Returns:
            ICCプロファイルのバイトデータ（存在しない場合はNone）
        """
        try:
            with Image(filename=file_path) as img:
                return img.profiles.get("icc")
        except Exception:
            return None

    def convert_to_srgb(self, image: Image, source_profile: bytes | None = None) -> Image:
        """画像をsRGBカラースペースに変換する。

        ICCプロファイルを使用して正確な色変換を行います。
        プロファイルが存在しない場合は色空間変換のみ行います。

        Args:
            image: 変換する画像（Wand Image）
            source_profile: ソースのICCプロファイル（Noneの場合はファイルから取得）

        Returns:
            sRGBに変換された画像
        """
        # 既にsRGBの場合はそのまま返す
        if image.colorspace == "srgb":
            return image

        # CMYKなどの場合はICCプロファイル変換で精度を上げる
        if source_profile and self._has_srgb_profile():
            try:
                # ソースプロファイルを設定してsRGBに変換
                image.profiles["icc"] = source_profile
                with open(self._get_srgb_profile_path(), "rb") as f:
                    srgb_profile = f.read()
                image.transform_colorspace("srgb")
                # sRGBプロファイルをアタッチ
                image.profiles["icc"] = srgb_profile
                return image
            except Exception:
                pass

        # フォールバック: 単純な色空間変換
        image.transform_colorspace("srgb")
        return image

    def _has_srgb_profile(self) -> bool:
        """sRGBプロファイルファイルが利用可能か確認する。

        Returns:
            利用可能な場合はTrue
        """
        return Path(self.SRGB_PROFILE_PATH).exists() or Path(self.SRGB_PROFILE_PATH_ALT).exists()

    def _get_srgb_profile_path(self) -> str:
        """利用可能なsRGBプロファイルのパスを返す。

        Returns:
            sRGBプロファイルのパス

        Raises:
            FileNotFoundError: sRGBプロファイルが見つからない場合
        """
        if Path(self.SRGB_PROFILE_PATH).exists():
            return self.SRGB_PROFILE_PATH
        if Path(self.SRGB_PROFILE_PATH_ALT).exists():
            return self.SRGB_PROFILE_PATH_ALT
        raise FileNotFoundError("sRGBカラープロファイルが見つかりません")
