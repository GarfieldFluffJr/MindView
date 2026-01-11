# SynthSeg-Based Brain Segmentation & 3D Rendering Spec

## Overview

This spec defines a pipeline to segment brain MRI scans using **SynthSeg** (for anatomical structures) combined with a **tumor detection model** (for pathological regions), then convert the segmentation into colored 3D meshes with interactive controls.

---

## Feasibility Assessment

### SynthSeg Capabilities
- **Strengths**: Contrast-agnostic segmentation works on any MRI (T1, T2, FLAIR, etc.) without preprocessing
- **Output**: 32+ anatomical brain regions (cortical, subcortical, ventricles, brainstem, cerebellum)
- **Performance**: ~15s on GPU, ~1min on CPU per scan
- **Limitation**: NOT designed for tumor/lesion segmentation - may produce incorrect labels in pathological regions

### Tumor Detection Requirement
SynthSeg does not detect tumors. For tumor detection, we need a separate model.

**Recommended Options (in order of preference):**

| Model | Dice Score | GPU Memory | Inference Time | Ease of Use |
|-------|------------|------------|----------------|-------------|
| MONAI Swin UNETR | ~90% | 8GB+ | ~30s | Medium |
| nnU-Net (KAIST BraTS21) | ~89% | 8GB+ | ~60s | Low |
| TotalSegmentator | ~85% | 4GB+ | ~45s | High |

**Primary Recommendation: MONAI Swin UNETR**
- Pre-trained on BraTS 2021 dataset (1,251 cases)
- State-of-the-art performance (~90% Dice)
- Segments 3 tumor regions: Enhancing Tumor (ET), Tumor Core (TC), Whole Tumor (WT)
- Requires 4 MRI modalities: T1, T1c (contrast), T2, FLAIR

**Fallback for Single-Modality MRI:**
- If user uploads single modality (e.g., only T1), use anomaly detection approach
- Compare against SynthSeg expected anatomy to identify abnormal regions

### Recommended Approach
1. Run SynthSeg for anatomical segmentation
2. Run tumor detection model separately (if available)
3. Merge results: tumor labels override anatomical labels where present
4. Convert combined segmentation to colored meshes

---

## Prerequisites

### 1. Python Environment
```bash
# Python 3.8+ required
cd apps/backend
python -m venv venv
source venv/bin/activate
```

### 2. Install SynthSeg
```bash
# Option A: Install from PyPI (if available)
pip install synthseg

# Option B: Install from source
git clone https://github.com/BBillot/SynthSeg.git
cd SynthSeg
pip install -e .

# Download pre-trained models
# Models are ~100MB each, download from UCL dropbox link in SynthSeg repo
mkdir -p apps/backend/models/synthseg
# Place downloaded .h5 model files in this directory
```

### 3. Install Additional Dependencies
```bash
pip install tensorflow>=2.0  # or tensorflow-gpu
pip install nibabel numpy scipy scikit-image trimesh
```

### 4. Tumor Detection Model (MONAI Swin UNETR)

```bash
# Install MONAI with all dependencies
pip install monai[all]

# Additional dependencies
pip install einops

# Create models directory
mkdir -p apps/backend/models/tumor

# Download pre-trained Swin UNETR weights (best fold - 90.59% Dice)
# Download from: https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/0.8.1/fold1_f48_ep300_4gpu_dice0_9059.zip
# Extract to: apps/backend/models/tumor/swin_unetr_brats21.pt
```

**All Available Pre-trained Weights:**

| Fold | Dice Score | Download URL |
|------|------------|--------------|
| 0 | 88.54% | https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/0.8.1/fold0_f48_ep300_4gpu_dice0_8854.zip |
| 1 | 90.59% | https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/0.8.1/fold1_f48_ep300_4gpu_dice0_9059.zip |
| 2 | 89.81% | https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/0.8.1/fold2_f48_ep300_4gpu_dice0_8981.zip |
| 3 | 89.24% | https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/0.8.1/fold3_f48_ep300_4gpu_dice0_8924.zip |
| 4 | 90.35% | https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/0.8.1/fold4_f48_ep300_4gpu_dice0_9035.zip |

---

## SynthSeg Label Mapping

SynthSeg outputs integer labels for each voxel. Key labels include:

| Label ID | Structure | Color (RGB) | Category |
|----------|-----------|-------------|----------|
| 0 | Background | - | - |
| 2 | Left Cerebral White Matter | [245, 245, 245] | White Matter |
| 3 | Left Cerebral Cortex | [205, 62, 78] | Cortex |
| 4 | Left Lateral Ventricle | [120, 18, 134] | Ventricle |
| 5 | Left Inferior Lateral Ventricle | [196, 58, 250] | Ventricle |
| 7 | Left Cerebellum White Matter | [220, 248, 164] | Cerebellum |
| 8 | Left Cerebellum Cortex | [230, 148, 34] | Cerebellum |
| 10 | Left Thalamus | [0, 118, 14] | Subcortical |
| 11 | Left Caudate | [122, 186, 220] | Subcortical |
| 12 | Left Putamen | [236, 13, 176] | Subcortical |
| 13 | Left Pallidum | [12, 48, 255] | Subcortical |
| 14 | 3rd Ventricle | [204, 182, 142] | Ventricle |
| 15 | 4th Ventricle | [42, 204, 164] | Ventricle |
| 16 | Brain Stem | [119, 159, 176] | Brainstem |
| 17 | Left Hippocampus | [220, 216, 20] | Subcortical |
| 18 | Left Amygdala | [103, 255, 255] | Subcortical |
| 24 | CSF | [60, 60, 60] | CSF |
| 26 | Left Accumbens | [255, 165, 0] | Subcortical |
| 28 | Left Ventral DC | [165, 42, 42] | Subcortical |
| 41 | Right Cerebral White Matter | [245, 245, 245] | White Matter |
| 42 | Right Cerebral Cortex | [205, 62, 78] | Cortex |
| 43 | Right Lateral Ventricle | [120, 18, 134] | Ventricle |
| 44 | Right Inferior Lateral Ventricle | [196, 58, 250] | Ventricle |
| 46 | Right Cerebellum White Matter | [220, 248, 164] | Cerebellum |
| 47 | Right Cerebellum Cortex | [230, 148, 34] | Cerebellum |
| 49 | Right Thalamus | [0, 118, 14] | Subcortical |
| 50 | Right Caudate | [122, 186, 220] | Subcortical |
| 51 | Right Putamen | [236, 13, 176] | Subcortical |
| 52 | Right Pallidum | [12, 48, 255] | Subcortical |
| 53 | Right Hippocampus | [220, 216, 20] | Subcortical |
| 54 | Right Amygdala | [103, 255, 255] | Subcortical |
| 58 | Right Accumbens | [255, 165, 0] | Subcortical |
| 60 | Right Ventral DC | [165, 42, 42] | Subcortical |

### Tumor Labels (Custom, from BraTS or user input)
| Label ID | Structure | Color (RGB) |
|----------|-----------|-------------|
| 100 | Necrotic Tumor Core | [255, 0, 0] |
| 101 | Peritumoral Edema | [255, 255, 0] |
| 102 | Enhancing Tumor | [255, 128, 0] |
| 103 | Non-Enhancing Tumor | [255, 64, 64] |

---

## Pipeline Architecture

```
Input: Patient MRI (.nii.gz)
│
├── Single Modality (T1 only)
│   │
│   ▼
│   ┌─────────────────────────────────────┐
│   │  Anomaly-Based Tumor Detection      │
│   │  - Statistical outlier detection    │
│   │  - Less accurate (~70% sensitivity) │
│   │  - Label: 103 (potential tumor)     │
│   └─────────────────────────────────────┘
│
└── Multi-Modal (T1 + T1c + T2 + FLAIR)
    │
    ▼
    ┌─────────────────────────────────────┐
    │  MONAI Swin UNETR (BraTS21)         │
    │  - Pre-trained on 1,251 cases       │
    │  - ~90% Dice accuracy               │
    │  - Labels: 100 (necrotic),          │
    │    101 (edema), 102 (enhancing)     │
    └─────────────────────────────────────┘

         │
         ▼ (parallel)
┌─────────────────────────────────────┐
│  Step 1: Run SynthSeg               │
│  - Input: T1-weighted MRI           │
│  - Output: Anatomical labels        │
│    (32+ brain structures)           │
│  - Contrast-agnostic                │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Step 2: Merge Segmentations        │
│  - Tumor labels (100-103) override  │
│    anatomical labels where present  │
│  - Preserve anatomical context      │
│    for non-tumor regions            │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Step 3: Generate Meshes            │
│  - One mesh per unique label        │
│  - Apply colors from lookup table   │
│  - Laplacian smoothing (5 iters)    │
│  - Export as GLB with metadata      │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Step 4: Render in Frontend         │
│  - Load GLB with named meshes       │
│  - Display region list with colors  │
│  - Visibility toggles per region    │
│  - Opacity sliders per region       │
│  - Tumor regions highlighted        │
│  - Isolation mode for focus         │
└─────────────────────────────────────┘
```

---

## Backend Implementation

### File Structure
```
apps/backend/
├── models/
│   ├── synthseg/
│   │   ├── synthseg_1.0.h5          # SynthSeg model weights
│   │   └── synthseg_robust.h5       # Robust variant
│   └── tumor/
│       └── swin_unetr_brats21.pt    # MONAI Swin UNETR weights (~300MB)
├── services/
│   ├── synthseg_service.py          # SynthSeg inference
│   ├── tumor_detection.py           # Tumor detection (MONAI Swin UNETR)
│   └── mesh_generation.py           # Segmentation to mesh
├── storage/
│   ├── uploads/
│   ├── segmentations/               # Intermediate .nii.gz
│   ├── meshes/                      # Output .glb files
│   └── metadata/                    # Output .json files
└── main.py
```

### Service: `synthseg_service.py`

```python
"""SynthSeg-based brain MRI segmentation service."""
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import nibabel as nib
import numpy as np

# SynthSeg label definitions
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

# Tumor labels (BraTS convention, remapped to avoid conflicts)
TUMOR_LABELS = {
    100: {"name": "necrotic_tumor_core", "color": [255, 0, 0], "category": "tumor"},
    101: {"name": "peritumoral_edema", "color": [255, 255, 0], "category": "tumor"},
    102: {"name": "enhancing_tumor", "color": [255, 128, 0], "category": "tumor"},
    103: {"name": "non_enhancing_tumor", "color": [255, 64, 64], "category": "tumor"},
}


def run_synthseg(
    input_path: Path,
    output_path: Path,
    use_robust: bool = False,
    use_gpu: bool = True
) -> bool:
    """
    Run SynthSeg segmentation on input MRI.

    Args:
        input_path: Path to input .nii.gz file
        output_path: Path for output segmentation .nii.gz
        use_robust: Use robust model for low-quality scans
        use_gpu: Use GPU acceleration

    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = [
            "python", "-m", "SynthSeg.predict",
            "--i", str(input_path),
            "--o", str(output_path),
        ]

        if use_robust:
            cmd.append("--robust")

        if not use_gpu:
            cmd.append("--cpu")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            print(f"SynthSeg error: {result.stderr}")
            return False

        return output_path.exists()

    except Exception as e:
        print(f"SynthSeg failed: {e}")
        return False


def get_label_info(label_id: int) -> dict:
    """Get label information by ID."""
    if label_id in SYNTHSEG_LABELS:
        return SYNTHSEG_LABELS[label_id]
    elif label_id in TUMOR_LABELS:
        return TUMOR_LABELS[label_id]
    else:
        return {"name": f"unknown_{label_id}", "color": [128, 128, 128], "category": "unknown"}


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

        # Remap BraTS labels (1,2,4) to our labels (100,101,102)
        tumor_remapped = np.zeros_like(tumor_data)
        tumor_remapped[tumor_data == 1] = 100  # Necrotic core
        tumor_remapped[tumor_data == 2] = 101  # Edema
        tumor_remapped[tumor_data == 4] = 102  # Enhancing tumor

        # Merge: tumor labels override anatomical
        merged_data[tumor_remapped > 0] = tumor_remapped[tumor_remapped > 0]

    # Get list of present labels
    unique_labels = np.unique(merged_data[merged_data > 0]).astype(int).tolist()

    # Save merged segmentation
    merged_img = nib.Nifti1Image(merged_data, anat_img.affine, anat_img.header)
    nib.save(merged_img, str(output_path))

    return merged_data, unique_labels
```

### Service: `tumor_detection.py`

```python
"""Brain tumor detection using MONAI Swin UNETR (BraTS21 pre-trained)."""
import os
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import nibabel as nib
import torch

# Check if MONAI is available
try:
    from monai.inferers import sliding_window_inference
    from monai.networks.nets import SwinUNETR
    from monai.transforms import (
        Compose,
        LoadImaged,
        NormalizeIntensityd,
        Orientationd,
        Spacingd,
        EnsureChannelFirstd,
        CropForegroundd,
        Resized,
    )
    MONAI_AVAILABLE = True
except ImportError:
    MONAI_AVAILABLE = False
    print("WARNING: MONAI not installed. Tumor detection will be disabled.")


# Model configuration
MODEL_PATH = Path(__file__).parent.parent / "models" / "tumor" / "swin_unetr_brats21.pt"
ROI_SIZE = (128, 128, 128)  # Input size for Swin UNETR
OVERLAP = 0.5  # Sliding window overlap


def is_tumor_model_available() -> bool:
    """Check if tumor detection model is available."""
    return MONAI_AVAILABLE and MODEL_PATH.exists()


def load_tumor_model(device: str = "cuda") -> Optional[torch.nn.Module]:
    """
    Load pre-trained Swin UNETR model for tumor segmentation.

    Args:
        device: "cuda" or "cpu"

    Returns:
        Loaded model or None if unavailable
    """
    if not is_tumor_model_available():
        return None

    try:
        # Initialize Swin UNETR architecture
        # BraTS uses 4 input channels (T1, T1c, T2, FLAIR) and 3 output classes
        model = SwinUNETR(
            img_size=ROI_SIZE,
            in_channels=4,  # T1, T1c, T2, FLAIR
            out_channels=3,  # ET, TC, WT (or background, non-enhancing, enhancing)
            feature_size=48,
            drop_rate=0.0,
            attn_drop_rate=0.0,
            dropout_path_rate=0.0,
            use_checkpoint=True,
        )

        # Load pre-trained weights
        checkpoint = torch.load(MODEL_PATH, map_location=device)
        model.load_state_dict(checkpoint["state_dict"])
        model.to(device)
        model.eval()

        print(f"Tumor detection model loaded successfully on {device}")
        return model

    except Exception as e:
        print(f"Failed to load tumor model: {e}")
        return None


def create_tumor_transforms():
    """Create preprocessing transforms for tumor detection."""
    return Compose([
        LoadImaged(keys=["image"]),
        EnsureChannelFirstd(keys=["image"]),
        Orientationd(keys=["image"], axcodes="RAS"),
        Spacingd(keys=["image"], pixdim=(1.0, 1.0, 1.0), mode="bilinear"),
        NormalizeIntensityd(keys=["image"], nonzero=True, channel_wise=True),
        CropForegroundd(keys=["image"], source_key="image"),
    ])


def run_tumor_detection(
    input_paths: list[Path],  # [T1, T1c, T2, FLAIR] paths
    output_path: Path,
    device: str = "cuda",
    job_id: str = ""
) -> bool:
    """
    Run tumor detection on multi-modal MRI.

    Args:
        input_paths: List of 4 NIfTI paths [T1, T1c, T2, FLAIR]
        output_path: Path for output segmentation .nii.gz
        device: "cuda" or "cpu"
        job_id: Job ID for logging

    Returns:
        True if successful and tumor found, False otherwise
    """
    if not is_tumor_model_available():
        print(f"[{job_id}] Tumor detection model not available")
        return False

    if len(input_paths) != 4:
        print(f"[{job_id}] Tumor detection requires 4 modalities (T1, T1c, T2, FLAIR)")
        return False

    try:
        model = load_tumor_model(device)
        if model is None:
            return False

        # Load and stack all modalities
        print(f"[{job_id}] Loading MRI modalities...")
        modalities = []
        affine = None

        for i, path in enumerate(input_paths):
            img = nib.load(str(path))
            if affine is None:
                affine = img.affine
            data = img.get_fdata()
            # Normalize each modality
            data = (data - data.mean()) / (data.std() + 1e-8)
            modalities.append(data)

        # Stack modalities: shape (4, H, W, D)
        stacked = np.stack(modalities, axis=0).astype(np.float32)

        # Convert to tensor and add batch dimension: (1, 4, H, W, D)
        tensor = torch.from_numpy(stacked).unsqueeze(0).to(device)

        print(f"[{job_id}] Running tumor inference...")
        with torch.no_grad():
            # Use sliding window inference for large volumes
            outputs = sliding_window_inference(
                tensor,
                ROI_SIZE,
                sw_batch_size=1,
                predictor=model,
                overlap=OVERLAP,
            )

            # Convert to segmentation labels
            # outputs shape: (1, 3, H, W, D) - probabilities for each class
            probs = torch.softmax(outputs, dim=1)
            seg = torch.argmax(probs, dim=1).squeeze(0).cpu().numpy()

        # Check if any tumor was detected
        tumor_voxels = np.sum(seg > 0)
        if tumor_voxels == 0:
            print(f"[{job_id}] No tumor detected")
            return False

        print(f"[{job_id}] Tumor detected: {tumor_voxels} voxels")

        # Remap labels to our convention:
        # Model output: 0=background, 1=non-enhancing/necrotic, 2=edema, 3=enhancing
        # Our labels: 100=necrotic, 101=edema, 102=enhancing
        tumor_remapped = np.zeros_like(seg, dtype=np.int16)
        tumor_remapped[seg == 1] = 100  # Necrotic/non-enhancing
        tumor_remapped[seg == 2] = 101  # Edema
        tumor_remapped[seg == 3] = 102  # Enhancing tumor

        # Save output
        output_img = nib.Nifti1Image(tumor_remapped, affine)
        nib.save(output_img, str(output_path))

        print(f"[{job_id}] Tumor segmentation saved to {output_path}")
        return True

    except Exception as e:
        print(f"[{job_id}] Tumor detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_single_modality_tumor_detection(
    input_path: Path,
    output_path: Path,
    device: str = "cuda",
    job_id: str = ""
) -> bool:
    """
    Fallback tumor detection for single-modality MRI.
    Uses anomaly detection by comparing against expected SynthSeg output.

    This is a simplified approach that:
    1. Runs SynthSeg to get expected anatomy
    2. Identifies regions with unexpected intensity patterns
    3. Flags anomalous regions as potential tumors

    Note: This is less accurate than multi-modal BraTS models.

    Args:
        input_path: Path to single modality MRI
        output_path: Path for output segmentation
        device: "cuda" or "cpu"
        job_id: Job ID for logging

    Returns:
        True if potential tumor found, False otherwise
    """
    try:
        print(f"[{job_id}] Running single-modality anomaly detection...")

        # Load input image
        img = nib.load(str(input_path))
        data = img.get_fdata()

        # Calculate global statistics
        non_zero = data[data > 0]
        if len(non_zero) == 0:
            return False

        mean_intensity = np.mean(non_zero)
        std_intensity = np.std(non_zero)

        # Flag regions with intensity > 2.5 standard deviations as potential tumor
        # This is a simple heuristic - real tumor detection should use trained models
        threshold = mean_intensity + 2.5 * std_intensity
        potential_tumor = (data > threshold).astype(np.int16)

        # Apply morphological operations to clean up noise
        from scipy.ndimage import binary_opening, binary_closing, label

        # Remove small noise
        potential_tumor = binary_opening(potential_tumor, iterations=2)
        potential_tumor = binary_closing(potential_tumor, iterations=2)

        # Find connected components
        labeled, num_features = label(potential_tumor)

        if num_features == 0:
            print(f"[{job_id}] No anomalous regions detected")
            return False

        # Keep only large connected components (potential tumors)
        min_tumor_size = 100  # Minimum voxels for a tumor region
        tumor_mask = np.zeros_like(data, dtype=np.int16)

        for i in range(1, num_features + 1):
            component = labeled == i
            if np.sum(component) >= min_tumor_size:
                tumor_mask[component] = 103  # Label as potential tumor

        if np.sum(tumor_mask > 0) == 0:
            print(f"[{job_id}] No significant anomalous regions found")
            return False

        print(f"[{job_id}] Potential tumor regions detected: {np.sum(tumor_mask > 0)} voxels")

        # Save output
        output_img = nib.Nifti1Image(tumor_mask, img.affine)
        nib.save(output_img, str(output_path))

        return True

    except Exception as e:
        print(f"[{job_id}] Single-modality tumor detection failed: {e}")
        return False
```

### Service: `mesh_generation.py`

```python
"""Convert segmentation labels to 3D meshes."""
from pathlib import Path
from typing import Optional
import json
import numpy as np
import nibabel as nib
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
import trimesh

from .synthseg_service import get_label_info, SYNTHSEG_LABELS, TUMOR_LABELS


def segmentation_to_meshes(
    segmentation_path: Path,
    output_glb_path: Path,
    output_metadata_path: Path,
    job_id: str,
    progress_callback=None,
    max_faces_per_region: int = 100000,
    smoothing_iterations: int = 5
) -> bool:
    """
    Convert a segmentation NIfTI to a GLB file with colored meshes.

    Args:
        segmentation_path: Path to segmentation .nii.gz
        output_glb_path: Path for output .glb file
        output_metadata_path: Path for output .json metadata
        job_id: Job ID for logging
        progress_callback: Optional callback(progress_percent)
        max_faces_per_region: Max faces per mesh for simplification
        smoothing_iterations: Laplacian smoothing iterations

    Returns:
        True if successful
    """
    print(f"[{job_id}] Loading segmentation...")
    img = nib.load(str(segmentation_path))
    data = img.get_fdata().astype(np.int32)
    spacing = img.header.get_zooms()[:3]

    # Get unique labels (excluding background)
    unique_labels = np.unique(data[data > 0]).astype(int).tolist()
    print(f"[{job_id}] Found {len(unique_labels)} regions")

    meshes = []
    regions_metadata = []

    for i, label_id in enumerate(unique_labels):
        if progress_callback:
            progress_callback(10 + int((i / len(unique_labels)) * 70))

        label_info = get_label_info(label_id)
        region_name = label_info["name"]
        color = label_info["color"]
        category = label_info["category"]

        print(f"[{job_id}] Processing {region_name} (label {label_id})...")

        # Create binary mask
        mask = (data == label_id).astype(np.float32)

        # Light smoothing
        mask_smoothed = gaussian_filter(mask, sigma=0.5)

        try:
            verts, faces, normals, _ = marching_cubes(
                mask_smoothed,
                level=0.5,
                spacing=spacing
            )

            if len(verts) == 0:
                print(f"[{job_id}] {region_name}: No vertices, skipping")
                continue

            mesh = trimesh.Trimesh(
                vertices=verts,
                faces=faces,
                vertex_normals=normals
            )

            # Apply smoothing
            trimesh.smoothing.filter_laplacian(mesh, iterations=smoothing_iterations)

            # Simplify if needed
            if len(mesh.faces) > max_faces_per_region:
                mesh = mesh.simplify_quadric_decimation(max_faces_per_region)
                print(f"[{job_id}] {region_name}: Simplified to {len(mesh.faces)} faces")

            # Apply color
            rgba = [color[0], color[1], color[2], 255]
            vertex_colors = np.tile(rgba, (len(mesh.vertices), 1)).astype(np.uint8)
            mesh.visual.vertex_colors = vertex_colors

            # Store metadata in mesh
            mesh.metadata["region_name"] = region_name
            mesh.metadata["label_id"] = label_id

            meshes.append(mesh)

            # Determine default visibility and opacity
            is_tumor = category == "tumor"
            is_outer = category in ["cortex", "white_matter", "cerebellum"]

            regions_metadata.append({
                "name": region_name,
                "label": region_name.replace("_", " ").title(),
                "labelId": label_id,
                "color": color,
                "category": category,
                "opacity": 1.0 if is_tumor else (0.3 if is_outer else 0.8),
                "defaultVisible": True if is_tumor else (False if is_outer else True),
            })

            print(f"[{job_id}] {region_name}: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

        except Exception as e:
            print(f"[{job_id}] {region_name} failed: {e}")
            continue

    if not meshes:
        raise ValueError("No meshes could be generated")

    # Create scene with named meshes
    if progress_callback:
        progress_callback(85)

    print(f"[{job_id}] Creating scene with {len(meshes)} meshes...")
    scene = trimesh.Scene()
    for mesh in meshes:
        region_name = mesh.metadata.get("region_name", "unknown")
        scene.add_geometry(mesh, node_name=region_name)

    # Export GLB
    if progress_callback:
        progress_callback(90)

    print(f"[{job_id}] Exporting to GLB...")
    scene.export(str(output_glb_path), file_type="glb")

    # Check for tumors
    has_tumor = any(r["category"] == "tumor" for r in regions_metadata)

    # Save metadata
    metadata = {
        "regions": regions_metadata,
        "has_tumor": has_tumor,
        "total_regions": len(regions_metadata),
        "segmentation_method": "synthseg",
    }

    with open(output_metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    if progress_callback:
        progress_callback(100)

    print(f"[{job_id}] Export complete")
    return True
```

### Updated `main.py` Integration

```python
# Add to main.py

from services.synthseg_service import run_synthseg, merge_segmentations
from services.tumor_detection import (
    is_tumor_model_available,
    run_tumor_detection,
    run_single_modality_tumor_detection
)
from services.mesh_generation import segmentation_to_meshes

SEGMENTATION_DIR = BASE_DIR / "storage" / "segmentations"
SEGMENTATION_DIR.mkdir(parents=True, exist_ok=True)

METADATA_DIR = BASE_DIR / "storage" / "metadata"
METADATA_DIR.mkdir(parents=True, exist_ok=True)


def process_nifti_with_synthseg(
    job_id: str,
    input_path: Path,
    output_path: Path,
    additional_modalities: list[Path] = None  # [T1c, T2, FLAIR] for tumor detection
) -> None:
    """
    Process NIfTI using SynthSeg segmentation + optional tumor detection.

    Args:
        job_id: Unique job identifier
        input_path: Path to primary MRI (T1)
        output_path: Path for output GLB mesh
        additional_modalities: Optional list of [T1c, T2, FLAIR] paths for tumor detection
    """
    metadata_path = METADATA_DIR / f"{job_id}.json"
    seg_path = SEGMENTATION_DIR / f"{job_id}_seg.nii.gz"
    tumor_path = SEGMENTATION_DIR / f"{job_id}_tumor.nii.gz"

    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 5

        def update_progress(p):
            jobs[job_id]["progress"] = p

        # Step 1: Run SynthSeg for anatomical segmentation
        print(f"[{job_id}] Running SynthSeg segmentation...")
        jobs[job_id]["progress"] = 10

        success = run_synthseg(input_path, seg_path, use_robust=True)
        if not success:
            raise ValueError("SynthSeg segmentation failed")

        jobs[job_id]["progress"] = 35

        # Step 2: Run tumor detection
        print(f"[{job_id}] Running tumor detection...")
        tumor_detected = False

        if additional_modalities and len(additional_modalities) == 3:
            # Multi-modal tumor detection (best accuracy)
            all_modalities = [input_path] + additional_modalities
            tumor_detected = run_tumor_detection(
                all_modalities,
                tumor_path,
                device="cuda" if torch.cuda.is_available() else "cpu",
                job_id=job_id
            )
        elif is_tumor_model_available():
            # Single-modality fallback
            print(f"[{job_id}] Using single-modality anomaly detection (less accurate)")
            tumor_detected = run_single_modality_tumor_detection(
                input_path,
                tumor_path,
                device="cuda" if torch.cuda.is_available() else "cpu",
                job_id=job_id
            )
        else:
            print(f"[{job_id}] Tumor detection model not available, skipping")

        jobs[job_id]["progress"] = 50

        # Step 3: Merge segmentations
        print(f"[{job_id}] Merging anatomical and tumor segmentations...")
        merged_path = SEGMENTATION_DIR / f"{job_id}_merged.nii.gz"
        merge_segmentations(
            seg_path,
            tumor_path if tumor_detected else None,
            merged_path
        )

        jobs[job_id]["progress"] = 55

        # Step 4: Generate meshes
        print(f"[{job_id}] Generating 3D meshes...")
        segmentation_to_meshes(
            merged_path,
            output_path,
            metadata_path,
            job_id,
            progress_callback=update_progress
        )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["mesh_path"] = str(output_path)
        jobs[job_id]["metadata_path"] = str(metadata_path)

        print(f"[{job_id}] Processing complete!")

    except Exception as e:
        print(f"[{job_id}] ERROR: {e}")
        import traceback
        traceback.print_exc()
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# Updated upload endpoint to support multi-modal uploads
@app.post("/api/upload")
async def upload_files(
    t1: UploadFile = File(..., description="Primary T1-weighted MRI"),
    t1c: UploadFile = File(None, description="T1-contrast MRI (optional, for tumor detection)"),
    t2: UploadFile = File(None, description="T2-weighted MRI (optional, for tumor detection)"),
    flair: UploadFile = File(None, description="FLAIR MRI (optional, for tumor detection)"),
):
    """
    Upload MRI files for segmentation.

    For best tumor detection, provide all 4 modalities (T1, T1c, T2, FLAIR).
    If only T1 is provided, basic anatomical segmentation will be performed
    with fallback anomaly-based tumor detection.
    """
    job_id = str(uuid.uuid4())

    # Save primary T1
    t1_path = UPLOAD_DIR / f"{job_id}_t1.nii.gz"
    content = await t1.read()
    with open(t1_path, "wb") as f:
        f.write(content)

    # Save additional modalities if provided
    additional_paths = []
    for modality, file in [("t1c", t1c), ("t2", t2), ("flair", flair)]:
        if file is not None:
            path = UPLOAD_DIR / f"{job_id}_{modality}.nii.gz"
            content = await file.read()
            with open(path, "wb") as f:
                f.write(content)
            additional_paths.append(path)

    # Initialize job
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "input_path": str(t1_path),
        "mesh_path": None,
        "error": None,
        "has_multimodal": len(additional_paths) == 3,
    }

    # Start processing
    output_path = MESH_DIR / f"{job_id}.glb"
    process_nifti_with_synthseg(
        job_id,
        t1_path,
        output_path,
        additional_paths if len(additional_paths) == 3 else None
    )

    return UploadResponse(
        job_id=job_id,
        status=jobs[job_id]["status"],
        message="Processing started" + (" with tumor detection" if len(additional_paths) == 3 else ""),
    )
```

---

## Frontend Implementation

### Updated `RegionControls.tsx`

The frontend should display:
1. **Grouped region list** by category (Cortex, Subcortical, Ventricles, Tumor, etc.)
2. **Visibility checkbox** for each region
3. **Opacity slider** for each region (0-100%)
4. **Color indicator** showing the region color
5. **"Show All" / "Hide All"** buttons per category
6. **"Isolate"** button to show only one region
7. **Tumor highlight** if tumor regions are present

### Metadata Response Structure

```typescript
interface RegionInfo {
  name: string;           // e.g., "left_hippocampus"
  label: string;          // e.g., "Left Hippocampus"
  labelId: number;        // e.g., 17
  color: [number, number, number];  // RGB
  category: string;       // e.g., "subcortical"
  opacity: number;        // 0.0 - 1.0
  defaultVisible: boolean;
}

interface MeshMetadata {
  job_id: string;
  regions: RegionInfo[];
  has_tumor: boolean;
  total_regions: number;
  segmentation_method: "synthseg";
}
```

### Category Grouping for UI

```typescript
const CATEGORY_ORDER = [
  { key: "tumor", label: "Tumor Regions", priority: 1 },
  { key: "subcortical", label: "Subcortical Structures", priority: 2 },
  { key: "ventricle", label: "Ventricles", priority: 3 },
  { key: "brainstem", label: "Brainstem", priority: 4 },
  { key: "cerebellum", label: "Cerebellum", priority: 5 },
  { key: "cortex", label: "Cerebral Cortex", priority: 6 },
  { key: "white_matter", label: "White Matter", priority: 7 },
  { key: "csf", label: "CSF", priority: 8 },
];
```

---

## API Endpoints

### POST `/api/upload`
- Accepts `.nii` or `.nii.gz` files
- Returns `job_id` for status polling

### GET `/api/status/{job_id}`
- Returns processing status and progress

### GET `/api/mesh/{job_id}`
- Returns GLB file with named meshes

### GET `/api/mesh/{job_id}/metadata`
- Returns JSON with region information

---

## Processing Time Estimates

| Step | GPU (8GB+) | CPU |
|------|------------|-----|
| SynthSeg anatomical segmentation | ~15s | ~60s |
| Swin UNETR tumor detection (multi-modal) | ~30s | ~180s |
| Single-modality anomaly detection | ~5s | ~10s |
| Merge segmentations | ~2s | ~2s |
| Mesh generation (35 regions) | ~30s | ~60s |
| **Total (with multi-modal tumor)** | **~1.5 min** | **~5 min** |
| **Total (single modality only)** | **~1 min** | **~2.5 min** |

**Memory Requirements:**
- Swin UNETR tumor model: 8GB+ GPU RAM
- SynthSeg: 4GB+ GPU RAM
- Mesh generation: 2GB+ RAM

---

## Limitations & Known Issues

1. **Multi-Modal Requirement for Best Tumor Detection**: Swin UNETR requires 4 MRI modalities (T1, T1c, T2, FLAIR) for accurate tumor segmentation (~90% Dice). Single-modality fallback uses anomaly detection which is less reliable.
2. **Pathological Brains**: SynthSeg may produce incorrect anatomical labels in areas affected by tumors/lesions. The tumor labels will override these regions after merging.
3. **Memory Usage**: Large MRI volumes may require 8GB+ GPU RAM for tumor detection, 4GB+ for SynthSeg.
4. **GPU Requirement**: For reasonable performance, GPU is strongly recommended. CPU inference takes 4-5x longer.
5. **Model Downloads**:
   - SynthSeg models (~100MB) must be downloaded from UCL repository
   - Swin UNETR weights (~300MB) must be downloaded from MONAI releases
6. **Input Requirements**:
   - BraTS tumor model expects specific preprocessing (1mm isotropic, skull-stripped)
   - Images from different scanners may need harmonization
7. **False Positives**: Anomaly-based single-modality detection may flag artifacts or normal anatomical variants as potential tumors. Always verify with clinical imaging.

---

## Implementation Order

1. **Phase 1: Basic SynthSeg Integration**
   - Install SynthSeg and dependencies
   - Implement `synthseg_service.py`
   - Test on sample MRI without tumors

2. **Phase 2: Mesh Generation**
   - Implement `mesh_generation.py`
   - Generate colored meshes from segmentation
   - Export with metadata

3. **Phase 3: Frontend Controls**
   - Update `RegionControls.tsx` for category grouping
   - Add per-region opacity sliders
   - Implement isolation mode

4. **Phase 4: Tumor Detection (Optional)**
   - Integrate BraTS model or alternative
   - Implement segmentation merging
   - Add tumor highlighting in UI

---

## Validation Checklist

### Anatomical Segmentation (SynthSeg)
- [ ] SynthSeg produces valid segmentation for test MRI
- [ ] All 32+ brain regions are correctly labeled
- [ ] Meshes render with correct colors per region
- [ ] Processing completes within 60s on GPU

### Tumor Detection (MONAI Swin UNETR)
- [ ] Tumor model loads successfully with pre-trained weights
- [ ] Multi-modal detection works with 4 modalities (T1, T1c, T2, FLAIR)
- [ ] Single-modality fallback activates when only T1 provided
- [ ] Tumor labels (100, 101, 102) correctly override anatomical labels
- [ ] Tumor regions render with distinct colors (red, yellow, orange)
- [ ] No false positives on healthy brain scans
- [ ] Processing completes within 90s on GPU

### Frontend Controls
- [ ] Region visibility toggles work
- [ ] Opacity sliders adjust transparency
- [ ] Isolation mode shows single region
- [ ] Category grouping displays correctly
- [ ] Tumor regions prominently highlighted in UI

### Error Handling
- [ ] Graceful fallback when tumor model unavailable
- [ ] Clear error messages for unsupported file formats
- [ ] Memory error handling for large volumes
- [ ] Timeout handling for long processing jobs

---

## References

### SynthSeg (Anatomical Segmentation)
- [SynthSeg GitHub Repository](https://github.com/BBillot/SynthSeg)
- [SynthSeg Paper (Medical Image Analysis)](https://www.sciencedirect.com/science/article/pii/S1361841523000506)

### Tumor Detection Models
- [MONAI Swin UNETR BraTS21 Tutorial](https://github.com/Project-MONAI/tutorials/blob/main/3d_segmentation/swin_unetr_brats21_segmentation_3d.ipynb)
- [MONAI Swin UNETR Research Repository](https://github.com/Project-MONAI/research-contributions/tree/main/SwinUNETR/BRATS21)
- [Swin UNETR Pre-trained Weights](https://github.com/Project-MONAI/MONAI-extra-test-data/releases/tag/0.8.1)
- [Swin UNETR Paper (arXiv)](https://arxiv.org/abs/2201.01266)
- [BraTS Challenge](https://www.med.upenn.edu/cbica/brats/)
- [nnU-Net Framework](https://github.com/MIC-DKFZ/nnUNet)
- [nnU-Net BraTS2020 Winner](https://link.springer.com/chapter/10.1007/978-3-030-72087-2_11)
- [KAIST BraTS21 Winner Implementation](https://github.com/rixez/Brats21_KAIST_MRI_Lab)

### Alternative Options (Not Recommended for Primary Use)
- [NVIDIA Clara Brain Tumor (Deprecated)](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/clara/containers/ai-braintumor)
- [TotalSegmentator MRI](https://github.com/wasserth/TotalSegmentator)
- [Hugging Face Tumor Detection Models](https://huggingface.co/hassaanik/Tumor_Detection)
