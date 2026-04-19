from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ローカル開発用（Docker環境）
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 100
    file_retention_hours: int = 24
    default_quality: int = 85
    max_delta_e: float = 2.0
    cors_origins: list[str] = ["*"]

    # AWS設定（Lambda/本番環境）
    s3_bucket: str = ""
    dynamodb_table: str = "chroma-sync-jobs"
    sqs_queue_url: str = ""
    aws_region: str = "ap-northeast-1"

    @property
    def use_aws(self) -> bool:
        """S3バケットが設定されていればAWSモードで動作する"""
        return bool(self.s3_bucket)

    class Config:
        env_file = ".env"


settings = Settings()
