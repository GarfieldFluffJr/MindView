"""Model manager for lazy loading and device detection."""
import os
from pathlib import Path
from typing import Optional
import requests
from tqdm import tqdm

from config import settings


class ModelManager:
    """Manages ML model loading, device detection, and downloads."""

    _device: Optional[str] = None
    _tumor_model = None

    @classmethod
    def get_device(cls) -> str:
        """Detect GPU availability, fallback to CPU."""
        if cls._device is not None:
            return cls._device

        try:
            import torch

            if settings.use_gpu and torch.cuda.is_available():
                cls._device = "cuda"
                print(f"Using GPU: {torch.cuda.get_device_name(0)}")
            elif settings.use_gpu and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                cls._device = "mps"
                print("Using Apple Silicon MPS")
            else:
                cls._device = "cpu"
                print("Using CPU (GPU not available)")
        except ImportError:
            cls._device = "cpu"
            print("PyTorch not available, using CPU")

        return cls._device

    @classmethod
    def get_tf_device(cls) -> str:
        """Get TensorFlow device string."""
        try:
            import tensorflow as tf

            gpus = tf.config.list_physical_devices("GPU")
            if settings.use_gpu and gpus:
                print(f"TensorFlow using GPU: {gpus[0].name}")
                return "/GPU:0"
            else:
                print("TensorFlow using CPU")
                return "/CPU:0"
        except ImportError:
            print("TensorFlow not available")
            return "/CPU:0"

    @classmethod
    def download_file(cls, url: str, dest_path: Path, desc: str = "Downloading") -> bool:
        """Download a file with progress bar."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            with open(dest_path, "wb") as f:
                with tqdm(total=total_size, unit="B", unit_scale=True, desc=desc) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            print(f"Downloaded: {dest_path}")
            return True

        except Exception as e:
            print(f"Download failed: {e}")
            if dest_path.exists():
                dest_path.unlink()
            return False

    @classmethod
    def ensure_tumor_model(cls) -> Path:
        """Ensure MONAI tumor model is downloaded, return path."""
        model_path = Path(settings.tumor_model_path)

        if model_path.exists():
            return model_path

        print(f"Tumor model not found at {model_path}")
        print("MONAI Swin UNETR model must be downloaded manually.")
        print("See: https://github.com/Project-MONAI/model-zoo")

        raise RuntimeError(
            "MONAI tumor model not found. Please download from MONAI model zoo."
        )

    @classmethod
    def ensure_models_dir(cls) -> Path:
        """Ensure models directory exists."""
        models_dir = Path(settings.models_dir)
        models_dir.mkdir(parents=True, exist_ok=True)
        (models_dir / "monai").mkdir(exist_ok=True)
        return models_dir


class SegmentationError(Exception):
    """Base exception for segmentation failures."""
    pass


class ModelLoadError(SegmentationError):
    """Failed to load ML model."""
    pass


class InferenceError(SegmentationError):
    """Inference failed."""
    pass


class GPUMemoryError(SegmentationError):
    """GPU out of memory, should retry on CPU."""
    pass
