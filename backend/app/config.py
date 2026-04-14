from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 100
    file_retention_hours: int = 24
    default_quality: int = 85
    max_delta_e: float = 2.0
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()
