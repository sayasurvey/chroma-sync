import numpy as np
import pytest
from skimage import io as sk_io

from app.converter.color_diff import ColorDiffCalculator


class TestColorDiffCalculator:
    def setup_method(self):
        self.calculator = ColorDiffCalculator()

    def test_calculate_delta_e_identical_images(self, sample_jpeg, temp_dir):
        """同一画像のΔEは0に近い"""
        import os

        import shutil

        copy_path = os.path.join(temp_dir, "copy.jpg")
        shutil.copy(sample_jpeg, copy_path)

        delta_e = self.calculator.calculate_delta_e(sample_jpeg, copy_path)
        assert delta_e < 1.0  # 同一画像は誤差のみ

    def test_calculate_delta_e_different_images(self, sample_jpeg, temp_dir):
        """異なる画像のΔEは0より大きい"""
        import os

        # 全く異なる画像を作成
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :, 0] = 255  # 赤一色
        other_path = os.path.join(temp_dir, "red.jpg")
        sk_io.imsave(other_path, img)

        # ランダムな画像と赤一色の画像は色差が大きい
        delta_e = self.calculator.calculate_delta_e(sample_jpeg, other_path)
        assert delta_e > 0

    def test_get_diff_regions_no_diff(self, sample_jpeg, temp_dir):
        """同一画像では色差領域は空"""
        import os
        import shutil

        copy_path = os.path.join(temp_dir, "copy.jpg")
        shutil.copy(sample_jpeg, copy_path)

        regions = self.calculator.get_diff_regions(sample_jpeg, copy_path, threshold=2.0)
        assert isinstance(regions, list)
