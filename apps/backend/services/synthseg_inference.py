"""Brain segmentation using ANTsPyNet (replaces SynthSeg for Python 3.12+ compatibility)."""
from pathlib import Path
from typing import Callable, Optional

import nibabel as nib
import numpy as np

from services.model_manager import InferenceError


def run_synthseg(
    input_path: Path,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]] = None
) -> np.ndarray:
    """
    Run brain segmentation using ANTsPyNet's deep_atropos.

    This provides tissue segmentation (CSF, gray matter, white matter, etc.)
    similar to SynthSeg but compatible with modern Python versions.

    Args:
        input_path: Path to input NIfTI file
        output_path: Path to save segmentation NIfTI
        progress_callback: Optional callback for progress updates

    Returns:
        Segmentation as numpy array with tissue labels
    """
    try:
        if progress_callback:
            progress_callback(15)

        print("Loading ANTsPyNet for brain segmentation...")

        import ants
        import antspynet

        if progress_callback:
            progress_callback(20)

        # Load the image with ANTs
        print(f"Loading image: {input_path}")
        img = ants.image_read(str(input_path))

        if progress_callback:
            progress_callback(25)

        # Run brain extraction first
        print("Running brain extraction...")
        brain_extraction = antspynet.brain_extraction(
            img,
            modality="t1",
            verbose=True
        )
        brain_mask = brain_extraction["brain_mask"]

        if progress_callback:
            progress_callback(40)

        # Apply mask to get brain-only image
        brain_img = img * brain_mask

        if progress_callback:
            progress_callback(45)

        # Run deep_atropos for tissue segmentation
        # This segments into: CSF, gray matter, white matter, deep gray matter, brainstem, cerebellum
        print("Running tissue segmentation (deep_atropos)...")
        atropos_result = antspynet.deep_atropos(
            brain_img,
            do_preprocessing=True,
            verbose=True
        )

        if progress_callback:
            progress_callback(75)

        # Get the segmentation image
        segmentation_img = atropos_result["segmentation_image"]

        # Convert to numpy and remap labels to match our expected format
        # deep_atropos labels: 0=background, 1=CSF, 2=gray matter, 3=white matter,
        #                      4=deep gray matter, 5=brainstem, 6=cerebellum
        segmentation = segmentation_img.numpy().astype(np.int32)

        # Remap to FreeSurfer-like labels for compatibility with our label system
        label_remap = {
            0: 0,    # Background
            1: 24,   # CSF
            2: 3,    # Gray matter -> left cerebral cortex
            3: 2,    # White matter -> left cerebral white matter
            4: 10,   # Deep gray matter -> left thalamus (subcortical)
            5: 16,   # Brainstem
            6: 8,    # Cerebellum -> left cerebellum cortex
        }

        remapped = np.zeros_like(segmentation)
        for old_label, new_label in label_remap.items():
            remapped[segmentation == old_label] = new_label

        if progress_callback:
            progress_callback(85)

        # Save the segmentation
        print(f"Saving segmentation to: {output_path}")

        # Get the original affine from nibabel for consistency
        orig_nib = nib.load(str(input_path))
        seg_nib = nib.Nifti1Image(remapped.astype(np.int16), orig_nib.affine)
        nib.save(seg_nib, str(output_path))

        # Report results
        unique_labels = np.unique(remapped[remapped > 0])
        print(f"Segmentation complete. Found {len(unique_labels)} tissue types: {unique_labels.tolist()}")

        if progress_callback:
            progress_callback(90)

        return remapped

    except ImportError as e:
        raise InferenceError(
            f"ANTsPyNet not installed. Run: pip install antspyx antspynet\nError: {e}"
        )
    except Exception as e:
        raise InferenceError(f"Brain segmentation failed: {e}")
