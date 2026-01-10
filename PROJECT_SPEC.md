# MindView - Project Specification

## Overview

MindView is a web application that allows users to upload MRI brain tumor scan files (.nii or .nii.gz format), process them into 3D mesh models using a Python backend, and interactively visualize the resulting brain models in a web browser using Three.js. The application is designed to work with tumor MRI datasets, with future capabilities for AI-powered tumor identification and collaborative annotation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MindView Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐      │
│   │                 │     │                 │     │                 │      │
│   │    Frontend     │────▶│     Backend     │────▶│   Processing    │      │
│   │   (Next.js)     │◀────│    (FastAPI)    │◀────│    Pipeline     │      │
│   │                 │     │                 │     │                 │      │
│   └─────────────────┘     └─────────────────┘     └─────────────────┘      │
│          │                        │                       │                │
│          │                        │                       │                │
│          ▼                        ▼                       ▼                │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐      │
│   │   Three.js      │     │   File Storage  │     │   NIfTI → Mesh  │      │
│   │   3D Viewer     │     │   (uploads/)    │     │   Conversion    │      │
│   └─────────────────┘     └─────────────────┘     └─────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Frontend (`apps/frontend/`)
| Technology | Purpose |
|------------|---------|
| Next.js 16 | React framework with App Router |
| TypeScript | Type-safe development |
| Tailwind CSS 4 | Styling and UI components |
| Three.js | 3D rendering engine |
| React Three Fiber | React bindings for Three.js |
| React Dropzone | File upload handling |

### Backend (`apps/backend/`)
| Technology | Purpose |
|------------|---------|
| FastAPI | Python web framework |
| Uvicorn | ASGI server |
| NiBabel | NIfTI file parsing |
| scikit-image | Image processing (marching cubes) |
| NumPy | Numerical operations |
| trimesh | Mesh manipulation and export |

### Data Processing (`data/scripts/`)
| Technology | Purpose |
|------------|---------|
| NiBabel | Load and parse NIfTI files |
| scikit-image | Marching cubes algorithm for mesh generation |
| scipy | Image filtering and smoothing |
| trimesh | Mesh simplification and export to GLB/GLTF |

---

## Core Features

### 1. File Upload
- Accept `.nii` and `.nii.gz` (NIfTI) brain scan files
- Drag-and-drop upload interface
- File validation (format, size limits)
- Upload progress indicator
- Maximum file size: 500MB

### 2. MRI Processing Pipeline
- Parse NIfTI file headers and voxel data
- Apply preprocessing (smoothing, thresholding)
- Generate 3D mesh using marching cubes algorithm
- Simplify mesh to reduce polygon count for web rendering
- Export to GLB format for efficient web delivery

### 3. 3D Visualization
- Interactive 3D brain model viewer
- Controls: rotate, pan, zoom
- Lighting and material adjustments
- Optional: cross-section/slice views
- Optional: color mapping for different brain regions

### 4. User Interface
- Clean, minimal design
- Upload state management (idle, uploading, processing, ready)
- Error handling with user-friendly messages
- Responsive layout for desktop and tablet

---

## API Endpoints

### Backend REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload NIfTI file |
| `GET` | `/api/status/{job_id}` | Get processing status |
| `GET` | `/api/mesh/{job_id}` | Download generated mesh (GLB) |
| `DELETE` | `/api/job/{job_id}` | Delete job and associated files |

### Request/Response Examples

**Upload File**
```http
POST /api/upload
Content-Type: multipart/form-data

Response:
{
  "job_id": "uuid-string",
  "status": "queued",
  "message": "File uploaded successfully"
}
```

**Check Status**
```http
GET /api/status/{job_id}

Response:
{
  "job_id": "uuid-string",
  "status": "processing" | "completed" | "failed",
  "progress": 75,
  "mesh_url": "/api/mesh/{job_id}" (if completed)
}
```

---

## Data Flow

```
1. User uploads .nii/.nii.gz file
         │
         ▼
2. Frontend sends file to backend /api/upload
         │
         ▼
3. Backend saves file, creates job, returns job_id
         │
         ▼
4. Backend processing pipeline:
   a. Load NIfTI with NiBabel
   b. Extract 3D voxel data
   c. Apply Gaussian smoothing
   d. Threshold to isolate brain tissue
   e. Run marching cubes to generate mesh
   f. Simplify mesh (reduce triangles)
   g. Export to GLB format
         │
         ▼
5. Frontend polls /api/status/{job_id}
         │
         ▼
6. When complete, frontend fetches GLB from /api/mesh/{job_id}
         │
         ▼
7. Three.js loads and renders the 3D brain model
```

---

## Project Structure

```
MindView/
├── apps/
│   ├── frontend/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # Main upload/viewer page
│   │   │   ├── globals.css
│   │   │   └── api/                  # Next.js API routes (proxy)
│   │   ├── components/
│   │   │   ├── FileUpload.tsx        # Drag-drop upload component
│   │   │   ├── ProcessingStatus.tsx  # Progress indicator
│   │   │   ├── BrainViewer.tsx       # Three.js 3D viewer
│   │   │   └── ViewerControls.tsx    # UI controls for viewer
│   │   ├── hooks/
│   │   │   ├── useUpload.ts          # Upload state management
│   │   │   └── useJobStatus.ts       # Polling for job status
│   │   ├── lib/
│   │   │   └── api.ts                # API client functions
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── backend/
│       ├── main.py                   # FastAPI application
│       ├── routers/
│       │   └── upload.py             # Upload endpoints
│       ├── services/
│       │   ├── processor.py          # NIfTI processing logic
│       │   └── mesh_generator.py     # Marching cubes + export
│       ├── models/
│       │   └── job.py                # Job status models
│       ├── storage/
│       │   ├── uploads/              # Uploaded NIfTI files
│       │   └── meshes/               # Generated GLB files
│       └── requirements.txt
│
├── data/
│   └── scripts/
│       └── main.py                   # Standalone processing scripts
│
├── PROJECT_SPEC.md
└── README.md
```

---

## Processing Pipeline Details

### Step 1: Load NIfTI File
```python
import nibabel as nib

img = nib.load('brain_scan.nii.gz')
data = img.get_fdata()  # 3D numpy array
affine = img.affine     # Transformation matrix
```

### Step 2: Preprocessing
```python
from scipy.ndimage import gaussian_filter

# Smooth to reduce noise
smoothed = gaussian_filter(data, sigma=1.0)

# Threshold to isolate brain tissue
threshold = smoothed > np.percentile(smoothed, 50)
```

### Step 3: Generate Mesh (Marching Cubes)
```python
from skimage.measure import marching_cubes

verts, faces, normals, values = marching_cubes(
    threshold,
    level=0.5,
    spacing=img.header.get_zooms()
)
```

### Step 4: Simplify and Export
```python
import trimesh

mesh = trimesh.Trimesh(vertices=verts, faces=faces)
mesh = mesh.simplify_quadric_decimation(target_faces=100000)
mesh.export('brain_model.glb')
```

---

## Frontend Components

### BrainViewer Component
```tsx
// Pseudo-code structure
import { Canvas } from '@react-three/fiber'
import { OrbitControls, useGLTF } from '@react-three/drei'

function BrainViewer({ meshUrl }: { meshUrl: string }) {
  const { scene } = useGLTF(meshUrl)

  return (
    <Canvas>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} />
      <primitive object={scene} />
      <OrbitControls />
    </Canvas>
  )
}
```

---

## Environment Variables

### Frontend (`.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (`.env`)
```
UPLOAD_DIR=./storage/uploads
MESH_DIR=./storage/meshes
MAX_FILE_SIZE_MB=500
CORS_ORIGINS=http://localhost:3000
```

---

## Development Setup

### Frontend
```bash
cd apps/frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

### Backend
```bash
cd apps/backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
# Runs on http://localhost:8000
```

---

## Dependencies

### Backend (`requirements.txt`)
```
fastapi>=0.109.0
uvicorn>=0.27.0
python-multipart>=0.0.6
nibabel>=5.2.0
numpy>=1.26.0
scipy>=1.12.0
scikit-image>=0.22.0
trimesh>=4.0.0
pyglet>=2.0.0  # For trimesh GLB export
```

### Frontend (`package.json` additions)
```json
{
  "dependencies": {
    "three": "^0.160.0",
    "@react-three/fiber": "^8.15.0",
    "@react-three/drei": "^9.92.0",
    "react-dropzone": "^14.2.0"
  }
}
```

---

## Error Handling

| Error | HTTP Code | User Message |
|-------|-----------|--------------|
| Invalid file format | 400 | "Please upload a valid NIfTI file (.nii or .nii.gz)" |
| File too large | 413 | "File exceeds maximum size of 500MB" |
| Processing failed | 500 | "Unable to process scan. Please try a different file." |
| Job not found | 404 | "Processing job not found" |

---

## Security Considerations

- Validate file headers, not just extensions
- Sanitize filenames before storage
- Implement rate limiting on upload endpoint
- Set appropriate CORS policies
- Auto-delete files after 24 hours (or configurable TTL)
- No user authentication required for MVP (add later if needed)

---

## Future Enhancements

1. **AI-Powered Brain Region Segmentation** - Integrate a deep learning segmentation model (e.g., U-Net, nnU-Net) to automatically identify and color-code different brain regions in the 3D model
2. **Tumor Identification** - AI-assisted detection and highlighting of tumors within the brain scan, with volume estimation and boundary visualization
3. **Annotation Tools** - Mark, label, and save regions of interest directly on the 3D model with support for notes and metadata
4. **Live Remote Collaboration** - Real-time multi-user annotation sessions with WebSocket-based synchronization, allowing medical professionals to collaboratively review and annotate scans remotely

---

## Success Criteria

- [ ] User can upload a .nii or .nii.gz file
- [ ] Backend successfully generates a 3D mesh from the scan
- [ ] Mesh loads and renders in the browser within 30 seconds of upload
- [ ] User can rotate, pan, and zoom the 3D model
- [ ] Application handles errors gracefully with clear feedback
- [ ] Works on Chrome, Firefox, Safari, and Edge

---

## References

- [NIfTI File Format](https://nifti.nimh.nih.gov/)
- [NiBabel Documentation](https://nipy.org/nibabel/)
- [Three.js Documentation](https://threejs.org/docs/)
- [React Three Fiber](https://docs.pmnd.rs/react-three-fiber/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Marching Cubes Algorithm](https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.marching_cubes)
