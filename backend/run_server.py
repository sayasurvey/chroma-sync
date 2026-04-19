"""
PyInstaller用のuvicornサーバーエントリーポイント。
Electronから子プロセスとして起動される。
"""
import multiprocessing
import os
import sys

# PyInstallerのマルチプロセス対応（Windows）
if sys.platform == "win32":
    multiprocessing.freeze_support()

# PyInstaller環境ではモジュールパスを調整
if getattr(sys, "frozen", False):
    # 実行ファイルと同じディレクトリをパスに追加
    bundle_dir = sys._MEIPASS  # type: ignore[attr-defined]
    sys.path.insert(0, bundle_dir)
    # アップロードディレクトリはOSのユーザーデータディレクトリを使用
    default_upload_dir = os.path.join(os.path.expanduser("~"), ".chroma-sync", "uploads")
else:
    default_upload_dir = os.path.join(os.path.dirname(__file__), "uploads")

os.environ.setdefault("UPLOAD_DIR", default_upload_dir)
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
