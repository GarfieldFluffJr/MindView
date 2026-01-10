# Atlas-Based Internal Brain Segmentation & 3D Rendering Spec

## Context
The current pipeline converts a single MRI volume (`.nii.gz`) into a 3D surface mesh (`.obj`) using marching cubes. This produces only an outer brain shell and does not expose internal anatomical structures.

This spec defines how to extend the pipeline using **atlas-based segmentation** to extract and render **distinct internal brain regions** (e.g., lobes, ventricles) as separate 3D meshes.

---

## Objective
Enable visualization of internal brain structures by:
1. Registering a labeled brain atlas to patient MRI space
2. Extracting anatomical regions as binary masks
3. Converting each region into its own 3D mesh
4. Rendering all structures as layered, toggleable meshes in the frontend

---

## High-Level Pipeline
Patient MRI (.nii.gz)
+
Brain Atlas Labels (.nii.gz)
↓
Atlas → Patient Registration
↓
Labeled Volume in Patient Space
↓
Binary Masks per Region
↓
Marching Cubes (per region)
↓
Multiple OBJ Meshes
↓
Layered 3D Visualization

---

## Atlas Selection

### Required Properties
- Pre-labeled anatomical regions
- Publicly available
- NIfTI format
- Aligned to standard MNI space

### Recommended Atlases
- Harvard–Oxford Cortical & Subcortical Atlas
- AAL (Automated Anatomical Labeling) Atlas

Only one atlas is required for MVP.

---

## Registration Strategy

### Goal
Align atlas labels to the patient MRI coordinate space.

### Requirements
- Use **affine registration only**
- No nonlinear warping required
- Registration must preserve label integrity (nearest-neighbor interpolation)

### Output
- Atlas labels resampled into patient MRI space
- Result is a labeled volume with integer region IDs

---

## Region Selection (MVP Scope)

Only extract a **small, high-value subset** of regions.

### Required Regions
- Ventricles
- Frontal lobe
- Temporal lobe
- Parietal lobe
- Occipital lobe

<!-- ### Optional (Stretch)
- Motor cortex
- Speech-related regions -->

Each region must correspond to one or more atlas label IDs.

---

## Mask Extraction

For each region:
- Create a binary mask:

mask = (atlas_labels == REGION_LABEL_ID)

- Masks must be aligned voxel-for-voxel with patient MRI

Each mask represents **one anatomical structure**.

---

## Mesh Generation

### Method
- Apply marching cubes independently to each binary mask
- Use a fixed isovalue (e.g., 0.5)

### Output
- One mesh per region
- Mesh format:
- OBJ (preferred, matches current pipeline)
- GLTF optional

### Naming Convention
brain_shell.obj
tumor.obj
ventricles.obj
frontal_lobe.obj
temporal_lobe.obj
parietal_lobe.obj
occipital_lobe.obj

---

## Rendering Requirements (Frontend)

### Scene Composition
- All meshes share the same coordinate space
- Each structure rendered as a separate mesh object

### Visual Styling

| Structure     | Opacity | Color            |
|--------------|---------|------------------|
| Brain shell  | ~30%    | Neutral gray    |
| Tumor        | 100%    | Red             |
| Ventricles   | 80%     | Blue            |
| Lobes        | 50–70%  | Distinct pastel |

---

### Interaction Controls
- Toggle visibility per structure
- Adjust opacity per structure
- Camera controls: rotate, pan, zoom

---

## Region Isolation Mode

### Behavior
- Selecting a region:
  - Hides all other anatomical structures
  - Keeps tumor visible
  - Centers camera on selected region

---

## Risk View (Atlas-Based)

### Definition
Risk is defined as **spatial proximity between tumor and atlas-defined regions**.

### Computation
- Compute minimum Euclidean distance between:
  - Tumor mesh vertices
  - Region mesh vertices

### Output
- Distance in millimeters
- Boolean risk flag (distance < threshold)

### Display
- Highlight region if within threshold
- Show text summary:

Tumor is within X mm of the motor cortex (atlas reference).

---

## Data Constraints
- No DICOM ingestion
- No user uploads
- One preloaded patient case is sufficient
- Timepoints may be simulated

---

## Non-Goals (Explicit)
- Patient-specific ML segmentation
- Clinical diagnosis
- Training models
- Regulatory compliance
- Fine-grained anatomical accuracy

---

## Validation Checklist
- Internal structures are visible inside brain shell
- Each structure can be toggled independently
- Tumor is spatially aligned with atlas regions
- Region isolation works as expected
- Risk view produces consistent distances

---

## Notes for Agentic Implementation
- Preserve existing NIfTI → OBJ logic
- Extend pipeline to support **multiple masks → multiple meshes**
- Treat atlas segmentation as **reference anatomy**, not ground truth
- Favor reliability and determinism over anatomical completeness

---

## Success Criteria
- The 3D scene no longer appears hollow
- Internal anatomical structures are visually distinct
- Region-based interaction and proximity analysis are functional