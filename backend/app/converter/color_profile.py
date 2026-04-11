import glob
from pathlib import Path

from wand.image import Image


class ColorProfileManager:
    """ICCカラープロファイルの読み取りとsRGBへの変換を管理するクラス"""

    # Display P3 ICCプロファイルの候補パス
    # sRGB より広色域のため、P3 モニター上で CMYK の色を正確に再現できる
    P3_PROFILE_PATHS = [
        "/usr/share/color/icc/DisplayP3.icc",   # プロジェクト同梱（最優先）
    ]

    # sRGB ICCプロファイルの候補パス（glob パターンも使用可）
    SRGB_PROFILE_PATHS = [
        # プロジェクト同梱プロファイル（macOS sRGB Profile）
        "/usr/share/color/icc/sRGB.icc",
        # Ghostscript の組み込み sRGB プロファイル（Debian 系）
        "/usr/share/color/icc/ghostscript/srgb.icc",
        "/usr/share/color/icc/ghostscript/default_rgb.icc",
        "/usr/share/color/icc/colord/sRGB.icc",
        "/usr/share/doc/icc-profiles/sRGB.icc",
        # Ghostscript バージョン別プロファイル（glob パターン）
        "/usr/share/ghostscript/*/iccprofiles/default_rgb.icc",
        "/usr/local/share/ghostscript/*/iccprofiles/default_rgb.icc",
    ]

    # CMYK ICCプロファイルの候補パス（USWebCoatedSWOP や JapanColor2001Coated など）
    CMYK_PROFILE_PATHS = [
        # プロジェクト同梱プロファイル（macOS Generic CMYK Profile）
        # macOS Preview と同等の CMYK→sRGB 変換を行うために最優先
        "/usr/share/color/icc/GenericCMYK.icc",
        # Ghostscript の組み込み CMYK プロファイル（Debian 系）
        "/usr/share/color/icc/ghostscript/default_cmyk.icc",
        "/usr/share/color/icc/colord/CMYK.icc",
        "/usr/share/color/icc/icc-profiles/JapanColor2001Coated.icc",
        "/usr/share/color/icc/icc-profiles/USWebCoatedSWOP.icc",
        # Ghostscript バージョン別プロファイル（glob パターン）
        "/usr/share/ghostscript/*/iccprofiles/default_cmyk.icc",
        "/usr/local/share/ghostscript/*/iccprofiles/default_cmyk.icc",
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

        ICCプロファイルを使用してlcms2による正確な色変換を行います。
        空/無効なICCプロファイルを持つPSD（空バイト b"" など）にも対応します。

        Args:
            image: 変換する画像（Wand Image）
            source_profile: ソースのICCプロファイル（Noneの場合は埋め込みプロファイルを使用）

        Returns:
            sRGBに変換された画像
        """
        srgb_path = self._find_profile(self.SRGB_PROFILE_PATHS)

        # sRGBプロファイルが見つからない場合はフォールバック
        if not srgb_path:
            if image.colorspace != "srgb":
                image.transform_colorspace("srgb")
            return image

        with open(srgb_path, "rb") as f:
            srgb_data = f.read()

        is_cmyk = image.colorspace in ("cmyk", "ycbcr")

        # 有効なプロファイルかどうかを len で判定（b"" は無効扱い）
        raw_embedded = image.profiles.get("icc")
        embedded_profile = raw_embedded if (raw_embedded and len(raw_embedded) > 0) else None
        valid_source = source_profile if (source_profile and len(source_profile) > 0) else None

        # 既存の無効プロファイル（空バイト等）を除去してから変換を行う
        # 残っていると lcms2 変換の妨げになる
        if raw_embedded is not None and embedded_profile is None:
            try:
                del image.profiles["icc"]
            except (KeyError, Exception):
                pass

        if valid_source and valid_source != embedded_profile:
            # 明示的に指定されたプロファイルでソースを上書き
            try:
                del image.profiles["icc"]
            except (KeyError, Exception):
                pass
            image.profiles["icc"] = valid_source
            image.profiles["icc"] = srgb_data
            image.transform_colorspace("srgb")
        elif embedded_profile:
            # 有効な埋め込みプロファイルを使って sRGB へ変換
            # (colorspace が "srgb" と報告されても Adobe RGB 等の場合があるためチェック不要)
            image.profiles["icc"] = srgb_data
            image.transform_colorspace("srgb")
        elif is_cmyk:
            # CMYK でプロファイルなし → デフォルト CMYK プロファイルを割り当てて変換
            cmyk_path = self._find_profile(self.CMYK_PROFILE_PATHS)
            if cmyk_path:
                with open(cmyk_path, "rb") as f:
                    image.profiles["icc"] = f.read()
                image.profiles["icc"] = srgb_data
            image.transform_colorspace("srgb")
            image.profiles["icc"] = srgb_data
        else:
            # RGB でプロファイルなし → sRGB と仮定してプロファイルを付与（変換なし）
            image.transform_colorspace("srgb")
            image.profiles["icc"] = srgb_data

        return image

    @staticmethod
    def _find_profile(candidates: list[str]) -> str | None:
        """候補パスのリストから最初に存在するプロファイルパスを返す。

        glob パターン（* を含むパス）にも対応しています。

        Args:
            candidates: 候補パスのリスト（glob パターン可）

        Returns:
            存在するパス（ない場合は None）
        """
        for path in candidates:
            if "*" in path:
                matches = sorted(glob.glob(path))
                if matches:
                    return matches[-1]  # 最新バージョンを優先
            elif Path(path).exists():
                return path
        return None
