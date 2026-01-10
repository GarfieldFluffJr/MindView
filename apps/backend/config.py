"""Configuration settings for the MindView backend."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB settings
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "mindview"
    gridfs_bucket_name: str = "scans"

    # File settings
    max_file_size_mb: int = 500

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
