import uuid
from pathlib import Path
from typing import Literal

import nibabel as nib
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
import trimesh

app = FastAPI(title="MindView API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
MESH_DIR = BASE_DIR / "storage" / "meshes"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MESH_DIR.mkdir(parents=True, exist_ok=True)

jobs: dict[str, dict] = {}


class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int
    mesh_url: str | None = None
    error: str | None = None


def process_nifti_to_mesh(job_id: str, input_path: Path, output_path: Path) -> None:
    """Convert NIfTI file to GLB mesh with multiple isosurfaces for internal structures."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        print(f"[{job_id}] Loading NIfTI file...")

        img = nib.load(str(input_path))
        data = img.get_fdata()
        spacing = img.header.get_zooms()[:3]
        print(f"[{job_id}] Data shape: {data.shape}, spacing: {spacing}")

        jobs[job_id]["progress"] = 20

        smoothed = gaussian_filter(data, sigma=1.0)
        print(f"[{job_id}] Smoothing complete")

        non_zero = smoothed[smoothed > 0]
        if len(non_zero) == 0:
            raise ValueError("No non-zero values in scan data")

        thresholds = [
            (np.percentile(non_zero, 30), [150, 180, 210, 255]),  # Outer surface
            (np.percentile(non_zero, 55), [100, 150, 200, 255]),  # Mid layer
            (np.percentile(non_zero, 75), [80, 120, 180, 255]),   # Inner structure
            (np.percentile(non_zero, 90), [200, 100, 100, 255]),  # Deep structures
        ]
        print(f"[{job_id}] Thresholds: {[t[0] for t in thresholds]}")

        jobs[job_id]["progress"] = 30

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

                # Simplify if too many faces
                if len(mesh.faces) > 100000:
                    try:
                        mesh = mesh.simplify_quadric_decimation(100000)
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

        jobs[job_id]["progress"] = 85

        if not meshes:
            raise ValueError("Could not generate any mesh surfaces from the scan")

        print(f"[{job_id}] Combining {len(meshes)} meshes...")
        combined_mesh = trimesh.util.concatenate(meshes)
        print(f"[{job_id}] Combined mesh: {len(combined_mesh.vertices)} vertices, {len(combined_mesh.faces)} faces")

        jobs[job_id]["progress"] = 95

        print(f"[{job_id}] Exporting to GLB...")
        combined_mesh.export(str(output_path), file_type="glb")
        print(f"[{job_id}] Export complete: {output_path}")

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["mesh_path"] = str(output_path)

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
async def upload_file(file: UploadFile = File(...)):
    """Upload a NIfTI or OBJ file and start processing."""
    print(f"=== Upload request received ===")
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

    with open(input_path, "wb") as f:
        f.write(content)
    print(f"File saved to {input_path}")

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
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

    return UploadResponse(
        job_id=job_id,
        status=jobs[job_id]["status"],
        message="File uploaded and processed",
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
        mesh_url=mesh_url,
        error=job.get("error"),
    )


@app.get("/api/mesh/{job_id}")
async def get_mesh(job_id: str):
    """Download the generated mesh file."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Mesh not ready yet")

    mesh_path = job.get("mesh_path")
    if not mesh_path or not Path(mesh_path).exists():
        raise HTTPException(status_code=404, detail="Mesh file not found")

    return FileResponse(
        mesh_path,
        media_type="model/gltf-binary",
        filename=f"{job_id}.glb",
    )
