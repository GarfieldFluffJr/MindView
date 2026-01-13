import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import nibabel as nib
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
import trimesh

from config import settings
from database import connect_to_mongo, close_mongo_connection, Database
from routes import patients, cases, files, timeline, notes, feedback
from services.synthseg_service import (
    get_label_info,
    detect_segmentation_type,
    remap_brats_labels,
    merge_segmentations,
    SYNTHSEG_LABELS,
    TUMOR_LABELS,
)
from services.mesh_generation import segmentation_to_meshes, intensity_to_meshes
from services.model_manager import SegmentationError
from services.tumor_inference import TumorInference, run_tumor_detection
from services.gridfs_service import upload_to_gridfs, stream_from_gridfs

app = FastAPI(title="MindView API", version="1.0.0")

# Parse CORS origins from comma-separated string
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup and shutdown events
@app.on_event("startup")
async def startup_db():
    """Connect to MongoDB on startup."""
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_db():
    """Close MongoDB connection on shutdown."""
    await close_mongo_connection()


# Include routers
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(cases.router, prefix="/api/cases", tags=["Medical Cases"])
app.include_router(files.router, prefix="/api/files", tags=["Scan Files"])
app.include_router(timeline.router, prefix="/api/timeline", tags=["Timeline"])
app.include_router(notes.router, prefix="/api/notes", tags=["Notes"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
MESH_DIR = BASE_DIR / "storage" / "meshes"
METADATA_DIR = BASE_DIR / "storage" / "metadata"
SEGMENTATION_DIR = BASE_DIR / "storage" / "segmentations"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MESH_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)
SEGMENTATION_DIR.mkdir(parents=True, exist_ok=True)

jobs: dict[str, dict] = {}


class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "segmenting", "meshing", "completed", "failed"]
    progress: int
    status_message: Optional[str] = None
    mesh_url: Optional[str] = None
    error: Optional[str] = None


def is_segmentation_data(data: np.ndarray) -> bool:
    """Check if the data appears to be a segmentation (discrete integer labels)."""
    unique_values = np.unique(data[data > 0])
    # Segmentation typically has few unique integer values
    if len(unique_values) < 50 and np.allclose(unique_values, unique_values.astype(int)):
        return True
    return False


def process_segmentation_to_mesh(job_id: str, data: np.ndarray, spacing: tuple, output_path: Path) -> None:
    """Generate meshes from segmentation labels - each label becomes a separate colored structure."""
    # Color palette for different brain regions (RGBA)
    label_colors = {
        1: [220, 180, 180, 255],   # Label 1 - light pink (e.g., necrotic tumor core)
        2: [180, 220, 180, 255],   # Label 2 - light green (e.g., edema)  
        3: [180, 180, 220, 255],   # Label 3 - light blue (e.g., enhancing tumor)
        4: [255, 200, 100, 255],   # Label 4 - orange (e.g., other structure)
        5: [200, 100, 200, 255],   # Label 5 - purple
        6: [100, 200, 200, 255],   # Label 6 - cyan
        7: [255, 150, 150, 255],   # Label 7 - salmon
        8: [150, 255, 150, 255],   # Label 8 - light green
        9: [150, 150, 255, 255],   # Label 9 - light blue
        10: [255, 255, 150, 255],  # Label 10 - yellow
    }
    default_color = [200, 200, 200, 255]  # Gray for unknown labels
    
    unique_labels = np.unique(data[data > 0]).astype(int)
    print(f"[{job_id}] Found {len(unique_labels)} segmentation labels: {unique_labels.tolist()}")
    
    meshes = []
    
    for i, label in enumerate(unique_labels):
        jobs[job_id]["progress"] = 30 + int((i / len(unique_labels)) * 50)
        print(f"[{job_id}] Processing label {label} ({i+1}/{len(unique_labels)})")
        
        # Create binary mask for this label
        mask = (data == label).astype(np.float32)
        
        # Light smoothing to reduce jagged edges
        mask_smoothed = gaussian_filter(mask, sigma=0.5)
        
        try:
            verts, faces, normals, _ = marching_cubes(
                mask_smoothed,
                level=0.5,
                spacing=spacing
            )
            
            if len(verts) == 0:
                print(f"[{job_id}] Label {label}: No vertices, skipping")
                continue
                
            print(f"[{job_id}] Label {label}: {len(verts)} vertices, {len(faces)} faces")
            
            mesh = trimesh.Trimesh(
                vertices=verts,
                faces=faces,
                vertex_normals=normals
            )

            # Apply Laplacian smoothing to reduce voxel blockiness
            trimesh.smoothing.filter_laplacian(mesh, iterations=5)

            # Simplify large meshes (higher limit for better quality)
            if len(mesh.faces) > 200000:
                try:
                    mesh = mesh.simplify_quadric_decimation(200000)
                    print(f"[{job_id}] Label {label}: Simplified to {len(mesh.faces)} faces")
                except Exception as simp_err:
                    print(f"[{job_id}] Label {label}: Simplification failed: {simp_err}")
            
            # Apply color for this label
            color = label_colors.get(int(label), default_color)
            vertex_colors = np.tile(color, (len(mesh.vertices), 1)).astype(np.uint8)
            mesh.visual.vertex_colors = vertex_colors
            
            meshes.append(mesh)
            print(f"[{job_id}] Label {label}: Added to meshes")
            
        except Exception as label_err:
            print(f"[{job_id}] Label {label} failed: {label_err}")
            continue
    
    return meshes


def process_intensity_to_mesh(job_id: str, data: np.ndarray, spacing: tuple) -> list:
    """Generate meshes from intensity data using multiple thresholds."""
    smoothed = gaussian_filter(data, sigma=1.0)
    print(f"[{job_id}] Smoothing complete")

    non_zero = smoothed[smoothed > 0]
    if len(non_zero) == 0:
        raise ValueError("No non-zero values in scan data")

    # Use thresholds that better separate tissue types
    thresholds = [
        (np.percentile(non_zero, 25), [150, 180, 210, 200]),  # Outer surface (more transparent)
        (np.percentile(non_zero, 50), [100, 150, 200, 220]),  # Mid layer
        (np.percentile(non_zero, 70), [80, 120, 180, 240]),   # Inner structure
        (np.percentile(non_zero, 85), [200, 100, 100, 255]),  # Deep structures (opaque)
    ]
    print(f"[{job_id}] Thresholds: {[t[0] for t in thresholds]}")

    meshes = []

    for i, (threshold_value, color) in enumerate(thresholds):
        jobs[job_id]["progress"] = 30 + (i * 15)
        print(f"[{job_id}] Processing layer {i+1}/4 at threshold {threshold_value:.2f}")

        try:
            verts, faces, normals, _ = marching_cubes(
                smoothed,
                level=threshold_value,
                spacing=spacing
            )
            print(f"[{job_id}] Layer {i+1}: {len(verts)} vertices, {len(faces)} faces")

            if len(verts) == 0:
                print(f"[{job_id}] Layer {i+1}: No vertices, skipping")
                continue

            mesh = trimesh.Trimesh(
                vertices=verts,
                faces=faces,
                vertex_normals=normals
            )

            # Apply Laplacian smoothing to reduce voxel blockiness
            trimesh.smoothing.filter_laplacian(mesh, iterations=10)

            # Simplify if too many faces (higher limit for better quality)
            if len(mesh.faces) > 300000:
                try:
                    mesh = mesh.simplify_quadric_decimation(300000)
                    print(f"[{job_id}] Layer {i+1}: Simplified to {len(mesh.faces)} faces")
                except Exception as simp_err:
                    print(f"[{job_id}] Layer {i+1}: Simplification failed: {simp_err}")

            # Apply vertex colors
            vertex_colors = np.tile(color, (len(mesh.vertices), 1)).astype(np.uint8)
            mesh.visual.vertex_colors = vertex_colors

            meshes.append(mesh)
            print(f"[{job_id}] Layer {i+1}: Added to meshes")

        except Exception as layer_err:
            print(f"[{job_id}] Layer {i+1} failed: {layer_err}")
            continue
    
    return meshes


def process_nifti_to_mesh(job_id: str, input_path: Path, output_path: Path) -> None:
    """Convert NIfTI file to GLB mesh with metadata - auto-detects segmentation vs intensity data."""
    metadata_path = METADATA_DIR / f"{job_id}.json"

    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        print(f"[{job_id}] Loading NIfTI file...")

        img = nib.load(str(input_path))
        data = img.get_fdata()
        spacing = img.header.get_zooms()[:3]
        print(f"[{job_id}] Data shape: {data.shape}, spacing: {spacing}")

        jobs[job_id]["progress"] = 15

        def update_progress(p):
            jobs[job_id]["progress"] = p

        # Detect if input is already segmented or raw intensity data
        seg_type = detect_segmentation_type(data)
        print(f"[{job_id}] Detected data type: {seg_type}")

        if seg_type == 'intensity':
            # Raw intensity data - generate intensity-based mesh
            print(f"[{job_id}] Processing as INTENSITY data")
            jobs[job_id]["status_message"] = "Generating intensity-based visualization..."

            intensity_to_meshes(
                input_path,
                output_path,
                metadata_path,
                job_id,
                progress_callback=update_progress
            )
        else:
            # Already segmented data (brats, synthseg, or simple labels)
            print(f"[{job_id}] Processing as SEGMENTATION data ({seg_type})")
            jobs[job_id]["status_message"] = "Generating 3D visualization from segmentation..."

            # If BraTS, remap labels first
            if seg_type == 'brats':
                print(f"[{job_id}] Remapping BraTS labels to standard format")
                remapped_data = remap_brats_labels(data)
                remapped_path = SEGMENTATION_DIR / f"{job_id}_remapped.nii.gz"
                remapped_img = nib.Nifti1Image(remapped_data, img.affine, img.header)
                nib.save(remapped_img, str(remapped_path))
                seg_input = remapped_path
            else:
                seg_input = input_path

            segmentation_to_meshes(
                seg_input,
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


def process_obj_to_glb(job_id: str, input_path: Path, output_path: Path) -> None:
    """Convert OBJ file to GLB mesh."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 30

        mesh = trimesh.load(str(input_path))

        jobs[job_id]["progress"] = 70

        mesh.export(str(output_path), file_type="glb")

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["mesh_path"] = str(output_path)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    patient_id: int,
    case_id: int,
    file: UploadFile = File(...),
    scan_date: Optional[str] = None
):
    """Upload a NIfTI or OBJ file and start processing."""
    print(f"=== Upload request received ===")
    print(f"Patient ID: {patient_id}, Case ID: {case_id}")
    print(f"Scan Date: {scan_date}")
    print(f"Filename: {file.filename}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    is_nifti = file.filename.endswith(".nii") or file.filename.endswith(".nii.gz")
    is_obj = file.filename.endswith(".obj")
    print(f"Is NIfTI: {is_nifti}, Is OBJ: {is_obj}")

    if not (is_nifti or is_obj):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload a .nii, .nii.gz, or .obj file",
        )

    job_id = str(uuid.uuid4())
    print(f"Job ID: {job_id}")

    if is_nifti:
        ext = ".nii.gz" if file.filename.endswith(".nii.gz") else ".nii"
    else:
        ext = ".obj"

    input_path = UPLOAD_DIR / f"{job_id}{ext}"
    output_path = MESH_DIR / f"{job_id}.glb"
    print(f"Input path: {input_path}")
    print(f"Output path: {output_path}")

    content = await file.read()
    print(f"File size: {len(content)} bytes")

    # Upload original file to GridFS
    print(f"Uploading original file to GridFS...")
    try:
        original_gridfs_id = await upload_to_gridfs(
            file_data=content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            metadata={
                "job_id": job_id,
                "patient_id": patient_id,
                "case_id": case_id,
                "file_type": "original"
            }
        )
        print(f"Original file uploaded to GridFS with ID: {original_gridfs_id}")
    except Exception as gridfs_err:
        print(f"ERROR: Failed to upload to GridFS: {gridfs_err}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file to database: {str(gridfs_err)}")

    # Also save to local disk for processing (temporary)
    with open(input_path, "wb") as f:
        f.write(content)
    print(f"File saved to local disk for processing: {input_path}")

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "status_message": "Processing uploaded file...",
        "input_path": str(input_path),
        "mesh_path": None,
        "error": None,
    }

    print(f"Starting processing...")
    if is_nifti:
        process_nifti_to_mesh(job_id, input_path, output_path)
    else:
        process_obj_to_glb(job_id, input_path, output_path)

    print(f"Processing complete. Status: {jobs[job_id]['status']}")
    print(f"Error: {jobs[job_id].get('error')}")

    # If processing succeeded, upload mesh to GridFS
    mesh_gridfs_id = None
    if jobs[job_id]["status"] == "completed" and output_path.exists():
        print(f"Uploading processed mesh to GridFS...")
        try:
            with open(output_path, "rb") as mesh_file:
                mesh_content = mesh_file.read()

            mesh_gridfs_id = await upload_to_gridfs(
                file_data=mesh_content,
                filename=f"{job_id}.glb",
                content_type="model/gltf-binary",
                metadata={
                    "job_id": job_id,
                    "patient_id": patient_id,
                    "case_id": case_id,
                    "file_type": "mesh"
                }
            )
            print(f"Mesh uploaded to GridFS with ID: {mesh_gridfs_id}")
        except Exception as mesh_gridfs_err:
            print(f"Warning: Failed to upload mesh to GridFS: {mesh_gridfs_err}")

    # Parse scan_date if provided
    scan_timestamp = datetime.utcnow()
    if scan_date:
        try:
            # Parse ISO format date string
            scan_timestamp = datetime.fromisoformat(scan_date.replace('Z', '+00:00'))
        except Exception as e:
            print(f"Warning: Failed to parse scan_date '{scan_date}': {e}")
            # Fall back to current time if parsing fails

    # Save file metadata to database
    file_doc = {
        "file_id": job_id,
        "job_id": job_id,
        "case_id": case_id,
        "patient_id": patient_id,
        "original_file": {
            "gridfs_id": original_gridfs_id,
            "filename": file.filename,
            "content_type": file.content_type or "application/octet-stream",
            "size_bytes": len(content),
            "file_type": "nifti" if is_nifti else "obj"
        },
        "processed_mesh": {
            "gridfs_id": mesh_gridfs_id,
            "size_bytes": len(mesh_content) if mesh_gridfs_id else None
        } if mesh_gridfs_id else None,
        "status": jobs[job_id]["status"],
        "progress": jobs[job_id]["progress"],
        "error": jobs[job_id].get("error"),
        "uploaded_at": datetime.utcnow(),
        "scan_timestamp": scan_timestamp,
        "metadata": {}
    }

    try:
        await Database.scan_files.insert_one(file_doc)
        print(f"File metadata saved to database")
    except Exception as db_err:
        print(f"Warning: Failed to save file metadata to database: {db_err}")

    return UploadResponse(
        job_id=job_id,
        status=jobs[job_id]["status"],
        message="File uploaded and processed",
    )


def process_multimodal_to_mesh(
    job_id: str,
    modality_paths: dict,
    output_path: Path,
    metadata_path: Path
) -> None:
    """
    Process multi-modal MRI (T1, T1ce, T2, FLAIR) for tumor detection and mesh generation.

    Pipeline:
    1. Run MONAI SegResNet tumor detection on all 4 modalities
    2. Generate 3D mesh from tumor segmentation
    """
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["status_message"] = "Starting tumor detection..."
        jobs[job_id]["progress"] = 5

        def update_progress(p):
            jobs[job_id]["progress"] = p

        t1ce_path = modality_paths["t1ce"]

        # Step 1: Run MONAI tumor detection
        print(f"[{job_id}] Step 1: Running tumor detection on multi-modal input...")
        jobs[job_id]["status_message"] = "Detecting tumors (MONAI SegResNet)..."

        tumor_output = SEGMENTATION_DIR / f"{job_id}_tumor.nii.gz"

        tumor_seg = run_tumor_detection(
            modality_paths,
            tumor_output,
            t1ce_path,  # T1ce as reference for affine/shape
            progress_callback=lambda p: update_progress(5 + int(p * 0.6))  # 5-65%
        )

        has_tumor = tumor_seg is not None and np.any(tumor_seg > 0)
        print(f"[{job_id}] Tumor detection complete. Tumor found: {has_tumor}")
        jobs[job_id]["progress"] = 70

        if not has_tumor:
            print(f"[{job_id}] No tumor detected in scan")
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["status_message"] = "No tumor detected"

            # Save empty metadata
            metadata = {
                "regions": [],
                "has_tumor": False,
                "total_regions": 0,
                "segmentation_method": "monai_tumor_detection",
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)
            return

        # Step 2: Generate mesh from tumor segmentation
        print(f"[{job_id}] Step 2: Generating 3D mesh from tumor segmentation...")
        jobs[job_id]["status_message"] = "Generating 3D visualization..."

        segmentation_to_meshes(
            tumor_output,
            output_path,
            metadata_path,
            job_id,
            progress_callback=lambda p: update_progress(70 + int(p * 0.3))  # 70-100%
        )

        # Update metadata with tumor flag
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            metadata["has_tumor"] = True
            metadata["segmentation_method"] = "monai_tumor_detection"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["mesh_path"] = str(output_path)
        jobs[job_id]["metadata_path"] = str(metadata_path)
        jobs[job_id]["status_message"] = "Processing complete!"
        print(f"[{job_id}] Tumor detection and mesh generation complete!")

    except Exception as e:
        print(f"[{job_id}] ERROR: {e}")
        import traceback
        traceback.print_exc()
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/api/upload-multimodal", response_model=UploadResponse)
async def upload_multimodal_files(
    patient_id: int,
    case_id: int,
    t1: UploadFile = File(...),
    t1ce: UploadFile = File(...),
    t2: UploadFile = File(...),
    flair: UploadFile = File(...),
    scan_date: Optional[str] = None
):
    """
    Upload 4 MRI modalities (T1, T1ce, T2, FLAIR) for combined segmentation.

    This endpoint runs both anatomical (ANTsPyNet) and tumor (MONAI SegResNet)
    segmentation, then merges the results into a single 3D visualization.
    """
    print(f"=== Multi-modal upload request received ===")
    print(f"Patient ID: {patient_id}, Case ID: {case_id}")
    print(f"Files: T1={t1.filename}, T1ce={t1ce.filename}, T2={t2.filename}, FLAIR={flair.filename}")

    # Validate all files are NIfTI
    for name, file in [("t1", t1), ("t1ce", t1ce), ("t2", t2), ("flair", flair)]:
        if not file.filename:
            raise HTTPException(status_code=400, detail=f"No file provided for {name}")
        if not (file.filename.endswith(".nii") or file.filename.endswith(".nii.gz")):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format for {name}. Please upload a .nii or .nii.gz file"
            )

    job_id = str(uuid.uuid4())
    print(f"Job ID: {job_id}")

    # Save all 4 files to GridFS and local disk
    modality_paths = {}
    modality_gridfs_ids = {}
    total_size = 0

    for name, file in [("t1", t1), ("t1ce", t1ce), ("t2", t2), ("flair", flair)]:
        ext = ".nii.gz" if file.filename.endswith(".nii.gz") else ".nii"
        file_path = UPLOAD_DIR / f"{job_id}_{name}{ext}"

        content = await file.read()
        total_size += len(content)

        # Upload to GridFS
        try:
            gridfs_id = await upload_to_gridfs(
                file_data=content,
                filename=file.filename,
                content_type=file.content_type or "application/octet-stream",
                metadata={
                    "job_id": job_id,
                    "patient_id": patient_id,
                    "case_id": case_id,
                    "modality": name,
                    "file_type": "original_multimodal"
                }
            )
            modality_gridfs_ids[name] = gridfs_id
            print(f"Uploaded {name} to GridFS with ID: {gridfs_id}")
        except Exception as gridfs_err:
            print(f"Warning: Failed to upload {name} to GridFS: {gridfs_err}")

        # Save to local disk for processing
        with open(file_path, "wb") as f:
            f.write(content)

        modality_paths[name] = file_path
        print(f"Saved {name}: {file_path} ({len(content)} bytes)")

    output_path = MESH_DIR / f"{job_id}.glb"
    metadata_path = METADATA_DIR / f"{job_id}.json"

    # Initialize job
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "status_message": "Preparing multi-modal processing...",
        "input_paths": {k: str(v) for k, v in modality_paths.items()},
        "mesh_path": None,
        "metadata_path": None,
        "error": None,
    }

    # Process synchronously (can be made async with background tasks if needed)
    print(f"Starting multi-modal processing...")
    process_multimodal_to_mesh(job_id, modality_paths, output_path, metadata_path)

    print(f"Processing complete. Status: {jobs[job_id]['status']}")

    # If processing succeeded, upload mesh to GridFS
    mesh_gridfs_id = None
    if jobs[job_id]["status"] == "completed" and output_path.exists():
        print(f"Uploading processed multimodal mesh to GridFS...")
        try:
            with open(output_path, "rb") as mesh_file:
                mesh_content = mesh_file.read()

            mesh_gridfs_id = await upload_to_gridfs(
                file_data=mesh_content,
                filename=f"{job_id}.glb",
                content_type="model/gltf-binary",
                metadata={
                    "job_id": job_id,
                    "patient_id": patient_id,
                    "case_id": case_id,
                    "file_type": "mesh",
                    "multimodal": True
                }
            )
            print(f"Multimodal mesh uploaded to GridFS with ID: {mesh_gridfs_id}")
        except Exception as mesh_gridfs_err:
            print(f"Warning: Failed to upload multimodal mesh to GridFS: {mesh_gridfs_err}")

    # Parse scan_date if provided
    scan_timestamp = datetime.utcnow()
    if scan_date:
        try:
            scan_timestamp = datetime.fromisoformat(scan_date.replace('Z', '+00:00'))
        except Exception as e:
            print(f"Warning: Failed to parse scan_date '{scan_date}': {e}")

    # Save file metadata to database
    file_doc = {
        "file_id": job_id,
        "job_id": job_id,
        "case_id": case_id,
        "patient_id": patient_id,
        "original_file": {
            "filename": f"multimodal_{t1.filename}",
            "content_type": "application/octet-stream",
            "size_bytes": total_size,
            "file_type": "multimodal_nifti",
            "modalities": {
                "t1": t1.filename,
                "t1ce": t1ce.filename,
                "t2": t2.filename,
                "flair": flair.filename
            },
            "modality_gridfs_ids": {k: str(v) for k, v in modality_gridfs_ids.items()} if modality_gridfs_ids else None
        },
        "processed_mesh": {
            "gridfs_id": mesh_gridfs_id,
            "size_bytes": len(mesh_content) if mesh_gridfs_id else None
        } if mesh_gridfs_id else None,
        "status": jobs[job_id]["status"],
        "progress": jobs[job_id]["progress"],
        "error": jobs[job_id].get("error"),
        "uploaded_at": datetime.utcnow(),
        "scan_timestamp": scan_timestamp,
        "metadata": {"multimodal": True}
    }

    try:
        await Database.scan_files.insert_one(file_doc)
        print(f"File metadata saved to database")
    except Exception as db_err:
        print(f"Warning: Failed to save file metadata to database: {db_err}")

    return UploadResponse(
        job_id=job_id,
        status=jobs[job_id]["status"],
        message="Multi-modal files uploaded and processed",
    )


@app.get("/api/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """Get the processing status of a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    mesh_url = f"/api/mesh/{job_id}" if job["status"] == "completed" else None

    return StatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        status_message=job.get("status_message"),
        mesh_url=mesh_url,
        error=job.get("error"),
    )


@app.get("/api/mesh/{job_id}")
async def get_mesh(job_id: str):
    """Download the generated mesh file from GridFS."""
    from bson import ObjectId

    # Check database for file metadata
    file_doc = await Database.scan_files.find_one({"job_id": job_id})

    if not file_doc:
        raise HTTPException(status_code=404, detail="Mesh file not found")

    if file_doc.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Mesh not ready yet")

    # Get GridFS ID from processed_mesh field
    processed_mesh = file_doc.get("processed_mesh")
    if not processed_mesh or not processed_mesh.get("gridfs_id"):
        # Fallback: Try local filesystem for old files
        mesh_path = MESH_DIR / f"{job_id}.glb"
        if mesh_path.exists():
            return FileResponse(
                mesh_path,
                media_type="model/gltf-binary",
                filename=f"{job_id}.glb",
            )
        raise HTTPException(status_code=404, detail="Mesh file not found in database")

    mesh_gridfs_id = processed_mesh["gridfs_id"]
    print(f"Streaming mesh from GridFS with ID: {mesh_gridfs_id}")

    # Stream file from GridFS
    return await stream_from_gridfs(
        file_id=ObjectId(mesh_gridfs_id),
        filename=f"{job_id}.glb",
        content_type="model/gltf-binary"
    )


@app.get("/api/mesh/{job_id}/metadata")
async def get_mesh_metadata(job_id: str):
    """Get metadata for the generated mesh including region information."""
    metadata_path = None

    # First check in-memory jobs dict
    if job_id in jobs:
        job = jobs[job_id]
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Mesh not ready yet")
        metadata_path = job.get("metadata_path")
    else:
        # Check database for existing file
        file_doc = await Database.scan_files.find_one({"job_id": job_id})
        if file_doc and file_doc.get("status") == "completed":
            # File exists in database, use default metadata path
            metadata_path = METADATA_DIR / f"{job_id}.json"

    if not metadata_path:
        metadata_path = METADATA_DIR / f"{job_id}.json"

    if not Path(metadata_path).exists():
        # Return minimal metadata if file doesn't exist
        return JSONResponse({
            "regions": [],
            "has_tumor": False,
            "total_regions": 0,
            "segmentation_method": "unknown",
        })

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    return JSONResponse(metadata)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "MindView API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "patients": "/api/patients",
            "cases": "/api/cases",
            "upload": "/api/upload",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": "connected"}
