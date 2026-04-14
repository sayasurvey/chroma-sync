import numpy as np
from skimage import color as sk_color
from skimage import io as sk_io

from app.models.result import Region


class ColorDiffCalculator:
    """CIEDE2000規格でΔEを計算し、色ずれ領域を特定するクラス"""

    # 色差を計算するためのダウンスケール係数（パフォーマンス向上）
    DOWNSAMPLE_FACTOR = 4

    def calculate_delta_e(self, image1_path: str, image2_path: str) -> float:
        """2枚の画像間の平均ΔE（CIEDE2000）を計算する。

        Args:
            image1_path: 参照画像のパス
            image2_path: 比較画像のパス

        Returns:
            平均ΔE値（値が小さいほど色差が少ない）
        """
        img1 = self._load_as_lab(image1_path)
        img2 = self._load_as_lab(image2_path)

        # サイズを合わせる
        img2 = self._resize_to_match(img2, img1.shape)

        delta_e = sk_color.deltaE_ciede2000(img1, img2)
        return float(np.mean(delta_e))

    def get_diff_regions(
        self, image1_path: str, image2_path: str, threshold: float = 2.0
    ) -> list[Region]:
        """ΔEが閾値を超えた領域を特定する。

        Args:
            image1_path: 参照画像のパス
            image2_path: 比較画像のパス
            threshold: ΔE閾値（デフォルト2.0）

        Returns:
            閾値を超えた領域のリスト
        """
        img1 = self._load_as_lab(image1_path)
        img2 = self._load_as_lab(image2_path)
        img2 = self._resize_to_match(img2, img1.shape)

        delta_e_map = sk_color.deltaE_ciede2000(img1, img2)

        # 閾値を超えたピクセルのマスクを作成
        mask = delta_e_map > threshold

        if not np.any(mask):
            return []

        # 連続した領域をバウンディングボックスで表現
        regions = self._extract_regions(mask, delta_e_map)
        return regions

    def _load_as_lab(self, image_path: str) -> np.ndarray:
        """画像をCIELab色空間として読み込む。

        Args:
            image_path: 画像ファイルのパス

        Returns:
            CIELab色空間の画像（numpy配列）
        """
        img_rgb = sk_io.imread(image_path)

        # グレースケールの場合はRGBに変換
        if img_rgb.ndim == 2:
            img_rgb = np.stack([img_rgb] * 3, axis=-1)

        # アルファチャンネルがある場合は除去
        if img_rgb.shape[-1] == 4:
            img_rgb = img_rgb[..., :3]

        # ダウンスケールで処理を高速化
        if self.DOWNSAMPLE_FACTOR > 1:
            img_rgb = img_rgb[:: self.DOWNSAMPLE_FACTOR, :: self.DOWNSAMPLE_FACTOR]

        # 0-255 → 0.0-1.0 に正規化
        img_float = img_rgb.astype(float) / 255.0

        return sk_color.rgb2lab(img_float)

    def _resize_to_match(self, img: np.ndarray, target_shape: tuple) -> np.ndarray:
        """画像を目標サイズにリサイズする。

        Args:
            img: リサイズする画像
            target_shape: 目標の形状

        Returns:
            リサイズされた画像
        """
        if img.shape == target_shape:
            return img

        from skimage.transform import resize

        return resize(img, target_shape, anti_aliasing=True)

    def _extract_regions(self, mask: np.ndarray, delta_e_map: np.ndarray) -> list[Region]:
        """マスクから色差領域を抽出する。

        大きな領域（全体の1%以上）のみを対象として、
        単純なグリッドベースの分割で領域を特定します。

        Args:
            mask: True/Falseのマスク配列
            delta_e_map: ΔE値の配列

        Returns:
            色差領域のリスト
        """
        from skimage.measure import label, regionprops

        labeled = label(mask)
        regions: list[Region] = []

        total_pixels = mask.size
        min_area = total_pixels * 0.001  # 全体の0.1%以上の領域のみ対象

        for prop in regionprops(labeled):
            if prop.area < min_area:
                continue

            y_min, x_min, y_max, x_max = prop.bbox
            region_delta_e = delta_e_map[mask & (labeled == prop.label)]

            regions.append(
                Region(
                    x=int(x_min * self.DOWNSAMPLE_FACTOR),
                    y=int(y_min * self.DOWNSAMPLE_FACTOR),
                    width=int((x_max - x_min) * self.DOWNSAMPLE_FACTOR),
                    height=int((y_max - y_min) * self.DOWNSAMPLE_FACTOR),
                    delta_e_before=float(np.mean(region_delta_e)),
                    delta_e_after=0.0,  # 補正後に更新
                )
            )

        return regions
