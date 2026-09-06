from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="config.env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./omr.db"

    max_batch_items: int = 50
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB per sheet image
    min_image_dimension: int = 200
    max_image_dimension: int = 6000

    allowed_content_types: list[str] = ["image/jpeg", "image/png"]

    minio_endpoint: str = "127.0.0.1:9010"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False
    minio_bucket: str = "omr-sheets"


settings = Settings()
