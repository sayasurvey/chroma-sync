import os
import tempfile

import numpy as np
import pytest
from fastapi.testclient import TestClient
from skimage import io as sk_io


@pytest.fixture
def client():
    """FastAPI テストクライアント"""
    from app.main import app

    return TestClient(app)


@pytest.fixture
def temp_dir():
    """一時ディレクトリ"""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_jpeg(temp_dir):
    """テスト用のサンプルJPEG画像を生成する"""
    # 100x100 のランダム画像
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    path = os.path.join(temp_dir, "sample.jpg")
    sk_io.imsave(path, img)
    return path


@pytest.fixture
def sample_png(temp_dir):
    """テスト用のサンプルPNG画像を生成する"""
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    path = os.path.join(temp_dir, "sample.png")
    sk_io.imsave(path, img)
    return path
