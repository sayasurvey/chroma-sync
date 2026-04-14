import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles


class FileManager:
    """アップロードファイルの管理クラス"""

    def __init__(self, upload_dir: str) -> None:
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, content: bytes, filename: str) -> str:
        """アップロードされたファイルを保存し、パスを返す。

        Args:
            content: ファイルのバイト内容
            filename: 元のファイル名

        Returns:
            保存されたファイルの絶対パス
        """
        file_id = uuid.uuid4().hex
        ext = Path(filename).suffix.lower()
        save_path = self.upload_dir / f"{file_id}{ext}"

        async with aiofiles.open(save_path, "wb") as f:
            await f.write(content)

        return str(save_path)

    def get_output_path(self, input_path: str, job_id: str) -> str:
        """変換後のJPEGファイルパスを生成する。

        Args:
            input_path: 元ファイルのパス
            job_id: ジョブID

        Returns:
            出力JPEGファイルのパス
        """
        output_dir = self.upload_dir / "output"
        output_dir.mkdir(exist_ok=True)
        return str(output_dir / f"{job_id}.jpg")

    async def cleanup_expired_files(self, retention_hours: int) -> int:
        """指定時間を超えたファイルを削除する。

        Args:
            retention_hours: ファイル保持時間（時間）

        Returns:
            削除されたファイルの数
        """
        threshold = datetime.utcnow() - timedelta(hours=retention_hours)
        deleted = 0

        for file_path in self.upload_dir.rglob("*"):
            if not file_path.is_file():
                continue
            mtime = datetime.utcfromtimestamp(file_path.stat().st_mtime)
            if mtime < threshold:
                try:
                    file_path.unlink()
                    deleted += 1
                except OSError:
                    pass

        return deleted

    def delete_file(self, file_path: str) -> None:
        """指定ファイルを削除する。

        Args:
            file_path: 削除するファイルのパス
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
