"""SynthSeg-based brain MRI segmentation service with label definitions."""
from pathlib import Path
from typing import Optional, Tuple
import nibabel as nib
import numpy as np

# SynthSeg label definitions with FreeSurfer-compatible colors
SYNTHSEG_LABELS = {
    0: {"name": "background", "color": [0, 0, 0], "category": "background"},
    2: {"name": "left_cerebral_wm", "color": [245, 245, 245], "category": "white_matter"},
    3: {"name": "left_cerebral_cortex", "color": [205, 62, 78], "category": "cortex"},
    4: {"name": "left_lateral_ventricle", "color": [120, 18, 134], "category": "ventricle"},
    5: {"name": "left_inf_lateral_ventricle", "color": [196, 58, 250], "category": "ventricle"},
    7: {"name": "left_cerebellum_wm", "color": [220, 248, 164], "category": "cerebellum"},
    8: {"name": "left_cerebellum_cortex", "color": [230, 148, 34], "category": "cerebellum"},
    10: {"name": "left_thalamus", "color": [0, 118, 14], "category": "subcortical"},
    11: {"name": "left_caudate", "color": [122, 186, 220], "category": "subcortical"},
    12: {"name": "left_putamen", "color": [236, 13, 176], "category": "subcortical"},
    13: {"name": "left_pallidum", "color": [12, 48, 255], "category": "subcortical"},
    14: {"name": "third_ventricle", "color": [204, 182, 142], "category": "ventricle"},
    15: {"name": "fourth_ventricle", "color": [42, 204, 164], "category": "ventricle"},
    16: {"name": "brainstem", "color": [119, 159, 176], "category": "brainstem"},
    17: {"name": "left_hippocampus", "color": [220, 216, 20], "category": "subcortical"},
    18: {"name": "left_amygdala", "color": [103, 255, 255], "category": "subcortical"},
    24: {"name": "csf", "color": [60, 60, 60], "category": "csf"},
    26: {"name": "left_accumbens", "color": [255, 165, 0], "category": "subcortical"},
    28: {"name": "left_ventral_dc", "color": [165, 42, 42], "category": "subcortical"},
    41: {"name": "right_cerebral_wm", "color": [245, 245, 245], "category": "white_matter"},
    42: {"name": "right_cerebral_cortex", "color": [205, 62, 78], "category": "cortex"},
    43: {"name": "right_lateral_ventricle", "color": [120, 18, 134], "category": "ventricle"},
    44: {"name": "right_inf_lateral_ventricle", "color": [196, 58, 250], "category": "ventricle"},
    46: {"name": "right_cerebellum_wm", "color": [220, 248, 164], "category": "cerebellum"},
    47: {"name": "right_cerebellum_cortex", "color": [230, 148, 34], "category": "cerebellum"},
    49: {"name": "right_thalamus", "color": [0, 118, 14], "category": "subcortical"},
    50: {"name": "right_caudate", "color": [122, 186, 220], "category": "subcortical"},
    51: {"name": "right_putamen", "color": [236, 13, 176], "category": "subcortical"},
    52: {"name": "right_pallidum", "color": [12, 48, 255], "category": "subcortical"},
    53: {"name": "right_hippocampus", "color": [220, 216, 20], "category": "subcortical"},
    54: {"name": "right_amygdala", "color": [103, 255, 255], "category": "subcortical"},
    58: {"name": "right_accumbens", "color": [255, 165, 0], "category": "subcortical"},
    60: {"name": "right_ventral_dc", "color": [165, 42, 42], "category": "subcortical"},
}

# Tumor labels (BraTS convention, remapped to avoid conflicts with SynthSeg)
TUMOR_LABELS = {
    100: {"name": "necrotic_tumor_core", "color": [255, 0, 0], "category": "tumor"},
    101: {"name": "peritumoral_edema", "color": [255, 255, 0], "category": "tumor"},
    102: {"name": "enhancing_tumor", "color": [255, 128, 0], "category": "tumor"},
    103: {"name": "non_enhancing_tumor", "color": [255, 64, 64], "category": "tumor"},
}

# BraTS original labels for detection
BRATS_LABELS = {
    1: 100,  # Necrotic/non-enhancing tumor core -> 100
    2: 101,  # Peritumoral edema -> 101
    4: 102,  # Enhancing tumor -> 102
}

# Simple labels for basic segmentations (1-10)
SIMPLE_LABELS = {
    1: {"name": "region_1", "color": [220, 180, 180], "category": "region"},
    2: {"name": "region_2", "color": [180, 220, 180], "category": "region"},
    3: {"name": "region_3", "color": [180, 180, 220], "category": "region"},
    4: {"name": "region_4", "color": [255, 200, 100], "category": "region"},
    5: {"name": "region_5", "color": [200, 100, 200], "category": "region"},
    6: {"name": "region_6", "color": [100, 200, 200], "category": "region"},
    7: {"name": "region_7", "color": [255, 150, 150], "category": "region"},
    8: {"name": "region_8", "color": [150, 255, 150], "category": "region"},
    9: {"name": "region_9", "color": [150, 150, 255], "category": "region"},
    10: {"name": "region_10", "color": [255, 255, 150], "category": "region"},
}


def get_label_info(label_id: int) -> dict:
    """Get label information by ID."""
    if label_id in SYNTHSEG_LABELS:
        return SYNTHSEG_LABELS[label_id]
    elif label_id in TUMOR_LABELS:
        return TUMOR_LABELS[label_id]
    elif label_id in SIMPLE_LABELS:
        return SIMPLE_LABELS[label_id]
    else:
        # Generate a color based on label ID for unknown labels
        hue = (label_id * 137) % 360
        r = int(128 + 127 * np.sin(np.radians(hue)))
        g = int(128 + 127 * np.sin(np.radians(hue + 120)))
        b = int(128 + 127 * np.sin(np.radians(hue + 240)))
        return {"name": f"region_{label_id}", "color": [r, g, b], "category": "unknown"}


def is_brats_segmentation(data: np.ndarray) -> bool:
    """
    Check if the data appears to be a BraTS-style tumor segmentation.

    BraTS format has labels: 1 (necrotic core), 2 (edema), 4 (enhancing tumor).
    To be classified as BraTS:
    - Must have at least 2 of the 3 BraTS labels present
    - All non-zero labels must be from {1, 2, 4}
    - Total labeled volume should be < 30% of brain volume (tumors are small)
    """
    unique_values = set(np.unique(data[data > 0]).astype(int))
    brats_labels = {1, 2, 4}  # Standard BraTS labels

    # All labels must be from the BraTS set
    if not unique_values.issubset(brats_labels):
        return False

    # Must have at least 2 of the 3 BraTS labels to be considered BraTS
    overlap = unique_values & brats_labels
    if len(overlap) < 2:
        return False

    # Tumor volume should be relatively small (< 30% of total non-zero volume)
    # A real brain segmentation would have much larger volume than a tumor
    total_voxels = np.prod(data.shape)
    labeled_voxels = np.sum(data > 0)
    volume_ratio = labeled_voxels / total_voxels

    # If the labeled region is more than 30% of the total volume,
    # it's probably a brain segmentation, not a tumor segmentation
    if volume_ratio > 0.30:
        return False

    return True


def is_synthseg_segmentation(data: np.ndarray) -> bool:
    """Check if the data appears to be a SynthSeg segmentation."""
    unique_values = set(np.unique(data[data > 0]).astype(int))
    synthseg_ids = set(SYNTHSEG_LABELS.keys())
    # If more than half of the labels are SynthSeg labels, it's likely SynthSeg
    overlap = len(unique_values & synthseg_ids)
    return overlap > len(unique_values) / 2


def remap_brats_labels(data: np.ndarray) -> np.ndarray:
    """Remap BraTS labels (1,2,4) to our tumor labels (100,101,102)."""
    remapped = np.zeros_like(data, dtype=np.int32)
    for brats_label, our_label in BRATS_LABELS.items():
        remapped[data == brats_label] = our_label
    return remapped


def merge_segmentations(
    anatomical_path: Path,
    tumor_path: Optional[Path],
    output_path: Path
) -> Tuple[np.ndarray, list]:
    """
    Merge anatomical and tumor segmentations.
    Tumor labels take precedence where present.

    Returns:
        Tuple of (merged_data, list_of_present_labels)
    """
    # Load anatomical segmentation
    anat_img = nib.load(str(anatomical_path))
    anat_data = anat_img.get_fdata().astype(np.int32)

    merged_data = anat_data.copy()

    if tumor_path and tumor_path.exists():
        # Load tumor segmentation
        tumor_img = nib.load(str(tumor_path))
        tumor_data = tumor_img.get_fdata().astype(np.int32)

        # Check if it's BraTS format and remap if needed
        if is_brats_segmentation(tumor_data):
            tumor_data = remap_brats_labels(tumor_data)

        # Merge: tumor labels override anatomical
        merged_data[tumor_data > 0] = tumor_data[tumor_data > 0]

    # Get list of present labels
    unique_labels = np.unique(merged_data[merged_data > 0]).astype(int).tolist()

    # Save merged segmentation
    merged_img = nib.Nifti1Image(merged_data, anat_img.affine, anat_img.header)
    nib.save(merged_img, str(output_path))

    return merged_data, unique_labels


def detect_segmentation_type(data: np.ndarray) -> str:
    """
    Detect the type of segmentation data.

    Returns:
        'brats': BraTS-style tumor segmentation
        'synthseg': SynthSeg anatomical segmentation
        'simple': Simple integer labels (1-10)
        'intensity': Raw intensity data (not segmentation)
    """
    unique_values = np.unique(data[data > 0])

    # Check if it's segmentation data (discrete integer values)
    if len(unique_values) < 100 and np.allclose(unique_values, unique_values.astype(int)):
        if is_brats_segmentation(data):
            return 'brats'
        elif is_synthseg_segmentation(data):
            return 'synthseg'
        else:
            return 'simple'

    return 'intensity'
