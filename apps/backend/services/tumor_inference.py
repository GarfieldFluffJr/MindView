"""MONAI Swin UNETR tumor inference wrapper for brain MRI segmentation.

This module requires multi-modal MRI input (T1, T1ce, T2, FLAIR) for accurate
tumor detection. For single-modality input, tumor detection is skipped.

The model outputs BraTS-style labels:
- 1: Necrotic/non-enhancing tumor core
- 2: Peritumoral edema
- 4: Enhancing tumor

These are remapped to our internal labels (100, 101, 102) to avoid conflicts
with SynthSeg anatomical labels.
"""
from pathlib import Path
from typing import Callable, Dict, Optional

import nibabel as nib
import numpy as np

from config import settings
from services.model_manager import ModelManager, ModelLoadError, InferenceError
from services.synthseg_service import remap_brats_labels


# Required modalities for tumor detection
REQUIRED_MODALITIES = ["t1", "t1ce", "t2", "flair"]


class TumorInference:
    """Wrapper for MONAI Swin UNETR tumor segmentation model."""

    _model = None
    _model_path: Optional[Path] = None

    @classmethod
    def is_available(cls) -> bool:
        """Check if MONAI and PyTorch are available."""
        try:
            import torch
            import monai
            return True
        except ImportError:
            return False

    @classmethod
    def load_model(cls):
        """Load MONAI Swin UNETR model (lazy loading)."""
        if cls._model is not None:
            return cls._model

        if not cls.is_available():
            raise ModelLoadError("MONAI or PyTorch not installed")

        try:
            import torch
            from monai.networks.nets import SwinUNETR

            # Get model path
            model_path = ModelManager.ensure_tumor_model()
            cls._model_path = model_path

            device = ModelManager.get_device()
            print(f"Loading MONAI Swin UNETR model from {model_path}...")

            # Initialize model architecture
            model = SwinUNETR(
                img_size=(128, 128, 128),
                in_channels=4,  # T1, T1ce, T2, FLAIR
                out_channels=4,  # Background + 3 tumor classes
                feature_size=48,
                use_checkpoint=True,
            )

            # Load weights
            state_dict = torch.load(str(model_path), map_location=device)
            model.load_state_dict(state_dict)
            model.to(device)
            model.eval()

            cls._model = model
            print("MONAI Swin UNETR model loaded successfully")
            return cls._model

        except Exception as e:
            raise ModelLoadError(f"Failed to load MONAI model: {e}")

    @classmethod
    def check_multimodal_input(cls, input_paths: Dict[str, Path]) -> bool:
        """Check if all required modalities are available."""
        for modality in REQUIRED_MODALITIES:
            if modality not in input_paths or not input_paths[modality].exists():
                return False
        return True

    @classmethod
    def preprocess(cls, input_paths: Dict[str, Path]) -> np.ndarray:
        """
        Preprocess multi-modal MRI for tumor detection.

        - Load all 4 modalities
        - Normalize each modality
        - Stack into 4-channel input
        - Resize to 128x128x128
        """
        import torch
        from scipy.ndimage import zoom

        target_shape = (128, 128, 128)
        volumes = []

        for modality in REQUIRED_MODALITIES:
            img = nib.load(str(input_paths[modality]))
            data = img.get_fdata().astype(np.float32)

            # Normalize
            p1, p99 = np.percentile(data[data > 0], [1, 99])
            data = np.clip(data, p1, p99)
            data = (data - p1) / (p99 - p1 + 1e-8)

            # Resize to target shape
            zoom_factors = [t / s for t, s in zip(target_shape, data.shape)]
            data = zoom(data, zoom_factors, order=1)

            volumes.append(data)

        # Stack modalities: (4, D, H, W)
        stacked = np.stack(volumes, axis=0)

        # Add batch dimension: (1, 4, D, H, W)
        return stacked[np.newaxis, ...]

    @classmethod
    def postprocess(
        cls,
        prediction: np.ndarray,
        original_shape: tuple,
        affine: np.ndarray
    ) -> np.ndarray:
        """
        Postprocess tumor segmentation.

        - Argmax to get labels
        - Resize back to original shape
        - Remap BraTS labels to our format
        """
        from scipy.ndimage import zoom

        # Get segmentation from softmax output
        seg = np.argmax(prediction.squeeze(), axis=0)

        # Map output channels to BraTS labels (0->0, 1->1, 2->2, 3->4)
        label_map = {0: 0, 1: 1, 2: 2, 3: 4}
        mapped = np.zeros_like(seg)
        for out_idx, brats_label in label_map.items():
            mapped[seg == out_idx] = brats_label

        # Resize to original shape
        zoom_factors = [o / p for o, p in zip(original_shape, mapped.shape)]
        mapped = zoom(mapped, zoom_factors, order=0)

        # Remap BraTS labels to our internal format (100, 101, 102)
        remapped = remap_brats_labels(mapped)

        return remapped

    @classmethod
    def predict(
        cls,
        input_paths: Dict[str, Path],
        output_path: Path,
        reference_path: Path,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Optional[np.ndarray]:
        """
        Run tumor segmentation on multi-modal MRI.

        Args:
            input_paths: Dict of modality -> path (t1, t1ce, t2, flair)
            output_path: Path to save tumor segmentation
            reference_path: Reference NIfTI for affine/shape
            progress_callback: Optional progress callback

        Returns:
            Tumor segmentation array or None if requirements not met
        """
        # Check if we have all required modalities
        if not cls.check_multimodal_input(input_paths):
            print("Tumor detection skipped: multi-modal input not available")
            print(f"Required modalities: {REQUIRED_MODALITIES}")
            print(f"Available: {list(input_paths.keys())}")
            return None

        if not cls.is_available():
            print("Tumor detection skipped: MONAI/PyTorch not installed")
            return None

        try:
            import torch

            if progress_callback:
                progress_callback(55)

            # Load reference for output shape
            ref_img = nib.load(str(reference_path))
            original_shape = ref_img.shape
            affine = ref_img.affine

            # Load model
            model = cls.load_model()
            device = ModelManager.get_device()

            if progress_callback:
                progress_callback(60)

            # Preprocess
            print("Preprocessing multi-modal input...")
            processed = cls.preprocess(input_paths)
            input_tensor = torch.from_numpy(processed).float().to(device)

            if progress_callback:
                progress_callback(65)

            # Run inference
            print("Running tumor detection...")
            with torch.no_grad():
                output = model(input_tensor)
                prediction = output.cpu().numpy()

            if progress_callback:
                progress_callback(70)

            # Postprocess
            print("Postprocessing tumor segmentation...")
            tumor_seg = cls.postprocess(prediction, original_shape, affine)

            # Save result
            tumor_img = nib.Nifti1Image(tumor_seg.astype(np.int16), affine)
            nib.save(tumor_img, str(output_path))

            # Check if any tumor was found
            tumor_voxels = np.sum(tumor_seg > 0)
            if tumor_voxels > 0:
                print(f"Tumor detected: {tumor_voxels} voxels")
            else:
                print("No tumor detected")

            return tumor_seg

        except Exception as e:
            raise InferenceError(f"Tumor inference failed: {e}")


def run_tumor_detection(
    input_paths: Dict[str, Path],
    output_path: Path,
    reference_path: Path,
    progress_callback: Optional[Callable[[int], None]] = None
) -> Optional[np.ndarray]:
    """Convenience function to run tumor detection."""
    return TumorInference.predict(
        input_paths,
        output_path,
        reference_path,
        progress_callback
    )
