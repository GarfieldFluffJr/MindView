"""Segmentation service for orchestrating brain MRI segmentation pipeline."""
from pathlib import Path
from typing import Callable, Optional, Tuple
import traceback

import nibabel as nib
import numpy as np

from services.model_manager import ModelManager, SegmentationError, InferenceError
from services.synthseg_service import merge_segmentations, SYNTHSEG_LABELS, TUMOR_LABELS


def run_auto_segmentation(
    input_path: Path,
    output_dir: Path,
    job_id: str,
    progress_callback: Optional[Callable[[int], None]] = None
) -> Tuple[Path, dict]:
    """
    Run automatic brain segmentation pipeline.

    Pipeline:
    1. Run SynthSeg for anatomical segmentation (32+ brain regions)
    2. (Future) Run MONAI for tumor detection if multi-modal available
    3. Merge segmentations if tumor detected
    4. Return path to final segmentation

    Args:
        input_path: Path to input MRI NIfTI file
        output_dir: Directory to save segmentation outputs
        job_id: Job ID for naming output files
        progress_callback: Optional callback for progress updates (0-100)

    Returns:
        Tuple of (segmentation_path, metadata_dict)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Output paths
    synthseg_path = output_dir / f"{job_id}_synthseg.nii.gz"
    merged_path = output_dir / f"{job_id}_merged.nii.gz"

    metadata = {
        "method": "synthseg",
        "has_tumor": False,
        "labels_found": [],
    }

    def update_progress(p: int):
        if progress_callback:
            # Scale SynthSeg progress (10-50) to fit in overall pipeline
            progress_callback(10 + int(p * 0.4))

    try:
        print(f"[{job_id}] Starting automatic segmentation...")
        print(f"[{job_id}] Input: {input_path}")

        # Ensure models directory exists
        ModelManager.ensure_models_dir()

        if progress_callback:
            progress_callback(5)

        # Step 1: Run SynthSeg
        print(f"[{job_id}] Running SynthSeg anatomical segmentation...")

        from services.synthseg_inference import run_synthseg

        try:
            segmentation = run_synthseg(
                input_path,
                synthseg_path,
                progress_callback=update_progress
            )

            # Get unique labels found
            unique_labels = np.unique(segmentation[segmentation > 0]).astype(int).tolist()
            metadata["labels_found"] = unique_labels
            print(f"[{job_id}] SynthSeg found {len(unique_labels)} brain regions")

        except Exception as e:
            print(f"[{job_id}] SynthSeg failed: {e}")
            traceback.print_exc()
            raise InferenceError(f"SynthSeg failed: {e}")

        if progress_callback:
            progress_callback(55)

        # Step 2: Check for tumor detection (future implementation)
        # For now, we skip tumor detection as it requires multi-modal input
        # TODO: Implement tumor detection with MONAI Swin UNETR
        tumor_path = None
        has_tumor = False

        # Check if any tumor labels are already in the data
        # (in case user uploaded BraTS-style segmentation)
        tumor_label_ids = set(TUMOR_LABELS.keys())
        if any(label in tumor_label_ids for label in unique_labels):
            has_tumor = True
            metadata["has_tumor"] = True
            print(f"[{job_id}] Tumor labels detected in segmentation")

        if progress_callback:
            progress_callback(60)

        # Step 3: Merge segmentations if tumor detected
        if tumor_path and Path(tumor_path).exists():
            print(f"[{job_id}] Merging anatomical and tumor segmentations...")
            merged_data, _ = merge_segmentations(
                synthseg_path,
                tumor_path,
                merged_path
            )
            final_path = merged_path
            metadata["has_tumor"] = True
        else:
            # No tumor, use SynthSeg output directly
            final_path = synthseg_path

        if progress_callback:
            progress_callback(65)

        print(f"[{job_id}] Segmentation complete: {final_path}")

        return final_path, metadata

    except SegmentationError:
        raise
    except Exception as e:
        print(f"[{job_id}] Segmentation failed: {e}")
        traceback.print_exc()
        raise SegmentationError(f"Auto-segmentation failed: {e}")


def fallback_to_intensity(
    input_path: Path,
    output_path: Path,
    metadata_path: Path,
    job_id: str,
    progress_callback: Optional[Callable[[int], None]] = None
) -> None:
    """
    Fallback to intensity-based mesh generation when segmentation fails.

    This uses the existing intensity_to_meshes function.
    """
    from services.mesh_generation import intensity_to_meshes

    print(f"[{job_id}] Falling back to intensity-based mesh generation...")

    intensity_to_meshes(
        input_path,
        output_path,
        metadata_path,
        job_id,
        progress_callback=progress_callback
    )


def get_segmentation_method_name(method: str) -> str:
    """Get human-readable name for segmentation method."""
    methods = {
        "synthseg": "SynthSeg (FreeSurfer)",
        "brats": "BraTS Tumor Segmentation",
        "simple": "Simple Label Segmentation",
        "intensity": "Intensity-based Layers",
    }
    return methods.get(method, method)
