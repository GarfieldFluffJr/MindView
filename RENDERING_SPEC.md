# Atlas-Based Internal Brain Segmentation & 3D Rendering Spec

## Context
The current pipeline converts a single MRI volume (`.nii.gz`) into a 3D surface mesh (`.glb`) using marching cubes. This produces only an outer brain shell and does not expose internal anatomical structures.

This spec defines how to extend the pipeline using **atlas-based segmentation** to extract and render **distinct internal brain regions** (e.g., lobes, ventricles) as separate 3D meshes.

---

## Prerequisites (Complete Before Implementation)

### 1. Install Required Python Packages
Add the following to `apps/backend/requirements.txt`:
```
antspyx>=0.4.2
```

Then run:
```bash
cd apps/backend
pip install antspyx
```

> **Note**: ANTsPy installation can take 10-15 minutes and requires ~2GB disk space.

### 2. Download Brain Atlas
Download the Harvard-Oxford atlas (included with FSL, but available standalone):

```bash
# Create atlas directory
mkdir -p apps/backend/storage/atlases

# Download Harvard-Oxford atlas files
curl -L -o apps/backend/storage/atlases/HarvardOxford-cort-maxprob-thr25-1mm.nii.gz \
  "https://github.com/neurodata/neuroparc/raw/master/atlases/label/Human/HarvardOxford-cort-maxprob-thr25-1mm.nii.gz"

curl -L -o apps/backend/storage/atlases/HarvardOxford-sub-maxprob-thr25-1mm.nii.gz \
  "https://github.com/neurodata/neuroparc/raw/master/atlases/label/Human/HarvardOxford-sub-maxprob-thr25-1mm.nii.gz"
```

### 3. Download MNI Template (for registration)
```bash
curl -L -o apps/backend/storage/atlases/MNI152_T1_1mm_brain.nii.gz \
  "https://github.com/neurodata/neuroparc/raw/master/atlases/label/Human/MNI152_T1_1mm_brain.nii.gz"
```

---

## Objective
Enable visualization of internal brain structures by:
1. Registering a labeled brain atlas to patient MRI space
2. Extracting anatomical regions as binary masks
3. Converting each region into its own 3D mesh
4. Rendering all structures as layered, toggleable meshes in the frontend

---

## High-Level Pipeline
```
Patient MRI (.nii.gz)
        +
Brain Atlas Labels (.nii.gz) + MNI Template
        ↓
Atlas → Patient Registration (ANTsPy affine)
        ↓
Labeled Volume in Patient Space
        ↓
Binary Masks per Region
        ↓
Marching Cubes (per region)
        ↓
Combined GLB with named mesh groups
        ↓
Layered 3D Visualization
```

---

## Atlas Selection

### Chosen Atlas: Harvard-Oxford
- **Cortical atlas**: 48 cortical regions
- **Subcortical atlas**: 21 subcortical regions (includes ventricles)
- Format: NIfTI (1mm resolution, MNI152 space)
- Location: `apps/backend/storage/atlases/`

### Atlas Label Mapping (MVP Regions)

| Region | Atlas | Label IDs |
|--------|-------|-----------|
| Lateral Ventricles | Subcortical | 3, 14 |
| Frontal Lobe | Cortical | 1, 2, 3, 4, 5, 6 |
| Temporal Lobe | Cortical | 9, 10, 15, 16 |
| Parietal Lobe | Cortical | 7, 8, 17, 18 |
| Occipital Lobe | Cortical | 19, 20, 21, 22 |

---

## Registration Strategy

### Library
**ANTsPy** - Python interface to ANTs (Advanced Normalization Tools)

### Method
```python
import ants

# Load images
patient_mri = ants.image_read("patient.nii.gz")
mni_template = ants.image_read("MNI152_T1_1mm_brain.nii.gz")
atlas_labels = ants.image_read("HarvardOxford-cort-maxprob-thr25-1mm.nii.gz")

# Register MNI template to patient space (affine only)
registration = ants.registration(
    fixed=patient_mri,
    moving=mni_template,
    type_of_transform="Affine"
)

# Apply same transform to atlas labels
atlas_in_patient_space = ants.apply_transforms(
    fixed=patient_mri,
    moving=atlas_labels,
    transformlist=registration["fwdtransforms"],
    interpolator="nearestNeighbor"  # Preserves integer labels
)
```

### Output
- Atlas labels resampled into patient MRI space
- Result is a labeled volume with integer region IDs
- Same dimensions as patient MRI

---

## Region Selection (MVP Scope)

Only extract a **small, high-value subset** of regions.

### Required Regions
| Region | Color (RGBA) | Opacity |
|--------|--------------|---------|
| Brain Shell | [180, 180, 180, 80] | 30% |
| Ventricles | [100, 150, 255, 200] | 80% |
| Frontal Lobe | [255, 180, 180, 180] | 70% |
| Temporal Lobe | [180, 255, 180, 180] | 70% |
| Parietal Lobe | [180, 180, 255, 180] | 70% |
| Occipital Lobe | [255, 255, 180, 180] | 70% |
| Tumor (if present) | [255, 80, 80, 255] | 100% |

---

## Mask Extraction

For each region:
```python
# Combine multiple atlas labels into one region mask
frontal_labels = [1, 2, 3, 4, 5, 6]
mask = np.isin(atlas_labels, frontal_labels).astype(np.float32)
```

- Masks must be aligned voxel-for-voxel with patient MRI
- Each mask represents **one anatomical structure**

---

## Mesh Generation

### Method
- Apply marching cubes independently to each binary mask
- Use a fixed isovalue (0.5)
- Apply Laplacian smoothing to reduce voxel artifacts
- Simplify meshes to max 100,000 faces per region

### Output Format
**Single GLB file** containing multiple named mesh groups:
- Matches current pipeline output format
- Each region stored as a separate mesh within the GLB
- Mesh names stored in GLB extras/metadata

### Mesh Metadata Structure
```json
{
  "regions": [
    {"name": "brain_shell", "label": "Brain Shell", "color": [180, 180, 180], "defaultVisible": true},
    {"name": "ventricles", "label": "Ventricles", "color": [100, 150, 255], "defaultVisible": true},
    {"name": "frontal_lobe", "label": "Frontal Lobe", "color": [255, 180, 180], "defaultVisible": true},
    {"name": "temporal_lobe", "label": "Temporal Lobe", "color": [180, 255, 180], "defaultVisible": true},
    {"name": "parietal_lobe", "label": "Parietal Lobe", "color": [180, 180, 255], "defaultVisible": true},
    {"name": "occipital_lobe", "label": "Occipital Lobe", "color": [255, 255, 180], "defaultVisible": true},
    {"name": "tumor", "label": "Tumor", "color": [255, 80, 80], "defaultVisible": true}
  ]
}
```

---

## API Changes

### New Endpoint: Get Mesh Metadata
```
GET /api/mesh/{job_id}/metadata

Response:
{
  "job_id": "uuid",
  "regions": [...],
  "has_tumor": false,
  "registration_quality": "good"
}
```

### Modified: Status Response
```json
{
  "job_id": "uuid",
  "status": "completed",
  "progress": 100,
  "mesh_url": "/api/mesh/{job_id}",
  "metadata_url": "/api/mesh/{job_id}/metadata"
}
```

---

## Rendering Requirements (Frontend)

### Scene Composition
- All meshes share the same coordinate space
- Each structure rendered as a separate mesh object

### Visual Styling

| Structure     | Opacity | Color            |
|--------------|---------|------------------|
| Brain shell  | ~30%    | Neutral gray     |
| Tumor        | 100%    | Red              |
| Ventricles   | 80%     | Blue             |
| Lobes        | 50–70%  | Distinct pastel  |

---

### Interaction Controls
- Toggle visibility per structure (checkbox list in sidebar)
- Adjust opacity per structure (slider)
- Camera controls: rotate, pan, zoom (existing TrackballControls)
- Clipping plane (existing implementation)

### Frontend Component Updates Required

1. **BrainViewer.tsx**: 
   - Parse GLB mesh groups as separate objects
   - Apply per-region materials based on metadata
   - Expose visibility/opacity controls per mesh

2. **New Component - RegionControls.tsx**:
   - Sidebar panel listing all regions
   - Checkbox for visibility toggle
   - Opacity slider per region
   - "Isolate" button per region

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
- User uploads patient MRI (.nii.gz); atlas is pre-loaded on server
- One preloaded atlas is sufficient
- Registration happens server-side during processing

---

## File Structure

```
apps/backend/
├── storage/
│   ├── atlases/
│   │   ├── HarvardOxford-cort-maxprob-thr25-1mm.nii.gz
│   │   ├── HarvardOxford-sub-maxprob-thr25-1mm.nii.gz
│   │   └── MNI152_T1_1mm_brain.nii.gz
│   ├── uploads/
│   └── meshes/
├── services/
│   └── atlas_registration.py  # New: ANTsPy registration logic
└── main.py
```

---

## Non-Goals (Explicit)
- Patient-specific ML segmentation
- Clinical diagnosis
- Training models
- Regulatory compliance
- Fine-grained anatomical accuracy
- Nonlinear/deformable registration (affine only for MVP)

---

## Known Limitations
1. **Registration accuracy**: Affine-only registration may not perfectly align atlas to patient anatomy, especially for abnormal brains or those with large tumors
2. **Processing time**: ANTsPy registration adds ~30-60 seconds to processing
3. **Atlas boundaries**: Lobe boundaries are approximate anatomical conventions, not precise divisions

---

## Implementation Order
1. Install ANTsPy and download atlas files (prerequisites)
2. Create `atlas_registration.py` service
3. Update `process_nifti_to_mesh()` to use atlas-based regions
4. Add metadata endpoint
5. Update frontend BrainViewer to handle multiple mesh groups
6. Add RegionControls component
7. Implement region isolation mode
8. Add risk view (stretch goal)

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