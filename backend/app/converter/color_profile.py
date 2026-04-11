from pathlib import Path

from wand.image import Image


class ColorProfileManager:
    """ICCカラープロファイルの読み取りとsRGBへの変換を管理するクラス"""

    # sRGB ICCプロファイルの候補パス
    SRGB_PROFILE_PATHS = [
        "/usr/share/color/icc/colord/sRGB.icc",
        "/usr/share/ghostscript/icc/default_rgb.icc",
        "/usr/share/color/icc/sRGB.icc",
        "/usr/share/doc/icc-profiles/sRGB.icc",
    ]

    # CMYK ICCプロファイルの候補パス（USWebCoatedSWOP や JapanColor2001Coated など）
    CMYK_PROFILE_PATHS = [
        "/usr/share/color/icc/colord/CMYK.icc",
        "/usr/share/ghostscript/icc/default_cmyk.icc",
        "/usr/share/color/icc/icc-profiles/JapanColor2001Coated.icc",
        "/usr/share/color/icc/icc-profiles/USWebCoatedSWOP.icc",
    ]

    def get_icc_profile(self, file_path: str) -> bytes | None:
        """ファイルからICCカラープロファイルを取得する。

        AI ファイルは PDF として読み込む必要があるため、
        wand の pdf: プレフィックスを使用します。

        Args:
            file_path: 画像ファイルのパス

        Returns:
            ICCプロファイルのバイトデータ（存在しない場合はNone）
        """
        try:
            ext = Path(file_path).suffix.lower()
            read_path = f"pdf:{file_path}[0]" if ext == ".ai" else file_path
            with Image(resolution=300) as img:
                img.read(filename=read_path)
                return img.profiles.get("icc")
        except Exception:
            return None

    def convert_to_srgb(self, image: Image, source_profile: bytes | None = None) -> Image:
        """画像をsRGBカラースペースに変換する。

        ICCプロファイルを使用して正確な色変換を行います。
        CMYK 画像の場合は CMYK→sRGB のプロファイル変換を試みます。

        Args:
            image: 変換する画像（Wand Image）
            source_profile: ソースのICCプロファイル（Noneの場合はファイルから取得）

        Returns:
            sRGBに変換された画像
        """
        is_cmyk = image.colorspace in ("cmyk", "ycbcr")

        # 既に sRGB でかつ CMYK でない場合はそのまま返す
        if image.colorspace == "srgb" and not is_cmyk:
            return image

        srgb_path = self._find_profile(self.SRGB_PROFILE_PATHS)

        if is_cmyk and srgb_path:
            try:
                # CMYK プロファイルを設定
                cmyk_path = self._find_profile(self.CMYK_PROFILE_PATHS)
                if source_profile:
                    image.profiles["icc"] = source_profile
                elif cmyk_path:
                    with open(cmyk_path, "rb") as f:
                        image.profiles["icc"] = f.read()

                # sRGB プロファイルを読み込んでカラースペース変換
                with open(srgb_path, "rb") as f:
                    srgb_data = f.read()
                image.transform_colorspace("srgb")
                image.profiles["icc"] = srgb_data
                return image
            except Exception:
                pass

        if source_profile and srgb_path:
            try:
                image.profiles["icc"] = source_profile
                with open(srgb_path, "rb") as f:
                    srgb_data = f.read()
                image.transform_colorspace("srgb")
                image.profiles["icc"] = srgb_data
                return image
            except Exception:
                pass

        # フォールバック: 単純な色空間変換
        image.transform_colorspace("srgb")
        return image

    @staticmethod
    def _find_profile(candidates: list[str]) -> str | None:
        """候補パスのリストから最初に存在するプロファイルパスを返す。

        Args:
            candidates: 候補パスのリスト

        Returns:
            存在するパス（ない場合は None）
        """
        for path in candidates:
            if Path(path).exists():
                return path
        return None
