import uuid
from pathlib import Path

import boto3
import botocore


class S3Storage:
    """S3ベースのファイルストレージ"""

    # API Gateway の 10MB ペイロード制限を回避するための閾値
    DIRECT_UPLOAD_LIMIT_BYTES = 8 * 1024 * 1024  # 8MB

    def __init__(self, bucket: str, region: str = "ap-northeast-1") -> None:
        self.bucket = bucket
        self.s3 = boto3.client("s3", region_name=region)

    async def save_upload(self, content: bytes, filename: str, job_id: str) -> str:
        """アップロードされたファイルをS3に保存し、S3キーを返す。

        Args:
            content: ファイルのバイト内容
            filename: 元のファイル名
            job_id: ジョブID

        Returns:
            S3オブジェクトキー
        """
        ext = Path(filename).suffix.lower()
        key = f"input/{job_id}/{uuid.uuid4().hex}{ext}"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=content)
        return key

    def get_output_key(self, job_id: str) -> str:
        """変換後JPEGのS3キーを生成する。"""
        return f"output/{job_id}/result.jpg"

    def download_to_path(self, key: str, local_path: str) -> None:
        """S3オブジェクトをローカルパスにダウンロードする。"""
        self.s3.download_file(self.bucket, key, local_path)

    def upload_from_path(self, local_path: str, key: str) -> None:
        """ローカルファイルをS3にアップロードする。"""
        self.s3.upload_file(local_path, self.bucket, key, ExtraArgs={"ContentType": "image/jpeg"})

    def generate_presigned_upload_url(
        self, filename: str, job_id: str, expires_in: int = 300
    ) -> tuple[str, str]:
        """S3への直接アップロード用の署名付きURLを生成する。

        API Gateway の 10MB 制限を超えるファイルに使用する。

        Returns:
            (upload_url, s3_key) のタプル
        """
        ext = Path(filename).suffix.lower()
        key = f"input/{job_id}/{uuid.uuid4().hex}{ext}"
        upload_url = self.s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )
        return upload_url, key

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """S3オブジェクトの署名付きURLを生成する。

        Args:
            key: S3オブジェクトキー
            expires_in: URLの有効期間（秒）

        Returns:
            署名付きURL
        """
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def object_exists(self, key: str) -> bool:
        """S3オブジェクトの存在確認。"""
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except botocore.exceptions.ClientError:
            return False

    def delete_object(self, key: str) -> None:
        """S3オブジェクトを削除する。"""
        self.s3.delete_object(Bucket=self.bucket, Key=key)
