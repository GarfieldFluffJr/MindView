"""Configuration settings for the MindView backend."""
from pathlib import Path
from pydantic_settings import BaseSettings

# Base directory (robust across local + Render)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # CORS settings
    cors_origins: str = "http://localhost:3000,http://localhost:5173,https://mind-view-gamma.vercel.app/"  # Comma-separated list of allowed origins

    # MongoDB settings
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "mindview"
    gridfs_bucket_name: str = "scans"

    # File settings
    max_file_size_mb: int = 500

    # Model settings for brain segmentation
    models_dir: str = str(BASE_DIR / "models")
    tumor_model_path: str = str(BASE_DIR / "./models/monai/swin_unetr_brats.pt")

    # Inference settings
    use_gpu: bool = True  # Try GPU first, fallback to CPU
    segmentation_timeout: int = 600  # 10 minutes max

    # Gemini API settings
    gemini_api_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
