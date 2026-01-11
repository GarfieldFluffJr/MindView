"""Timeline morphing API endpoints."""
import asyncio
from datetime import datetime
from typing import List
from pathlib import Path
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from database import Database
from models.timeline import (
    TimelineMetadata, TimelineScanInfo, TimelineGenerateRequest,
    TimelineJobStatus
)
from services.timeline_processor import process_timeline_generation, TIMELINE_MESH_DIR

router = APIRouter()

# In-memory job tracking for progress updates
timeline_jobs: dict[str, dict] = {}


def update_job_progress(job_id: str, progress: int, step: str):
    """Update progress for a timeline job."""
    if job_id in timeline_jobs:
        timeline_jobs[job_id]["progress"] = progress
        timeline_jobs[job_id]["current_step"] = step


async def run_timeline_processing(
    job_id: str,
    patient_id: int,
    case_id: int,
    scan_job_ids: List[str],
    scan_timestamps: List[datetime],
    frames_between: int
):
    """Background task to run timeline processing."""
    import traceback

    try:
        print(f"[Timeline {job_id}] Starting processing...")
        timeline_jobs[job_id]["status"] = "processing"
        timeline_jobs[job_id]["current_step"] = "Starting..."

        # Run the processing
        mesh_path = await process_timeline_generation(
            job_id=job_id,
            patient_id=patient_id,
            case_id=case_id,
            scan_job_ids=scan_job_ids,
            scan_timestamps=scan_timestamps,
            frames_between=frames_between,
            update_progress=update_job_progress
        )

        print(f"[Timeline {job_id}] Processing complete, updating status...")

        # Update job status
        timeline_jobs[job_id]["status"] = "completed"
        timeline_jobs[job_id]["progress"] = 100
        timeline_jobs[job_id]["mesh_path"] = mesh_path
        timeline_jobs[job_id]["current_step"] = "Complete"

        # Update database
        await Database.db["timeline_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "mesh_path": mesh_path
            }}
        )
        print(f"[Timeline {job_id}] Done!")

    except Exception as e:
        error_msg = str(e)
        print(f"[Timeline {job_id}] ERROR: {error_msg}")
        traceback.print_exc()

        timeline_jobs[job_id]["status"] = "failed"
        timeline_jobs[job_id]["error"] = error_msg
        timeline_jobs[job_id]["current_step"] = f"Failed: {error_msg}"
        timeline_jobs[job_id]["progress"] = 0

        # Update database
        try:
            await Database.db["timeline_jobs"].update_one(
                {"job_id": job_id},
                {"$set": {
                    "status": "failed",
                    "error": error_msg
                }}
            )
        except Exception as db_err:
            print(f"[Timeline {job_id}] Failed to update DB: {db_err}")


@router.get("/status/{job_id}", response_model=TimelineJobStatus)
async def get_timeline_status(job_id: str):
    """Get status of timeline generation job."""
    # Helper to safely convert to int
    def safe_int(val, default=0):
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    # First check in-memory jobs dict
    if job_id in timeline_jobs:
        job = timeline_jobs[job_id]
        mesh_url = f"/api/timeline/mesh/{job_id}" if job.get("status") == "completed" else None

        return TimelineJobStatus(
            job_id=job_id,
            status=job.get("status", "queued"),
            progress=safe_int(job.get("progress"), 0),
            current_step=job.get("current_step"),
            mesh_url=mesh_url,
            error=job.get("error"),
            total_frames=safe_int(job.get("total_frames")),
            frames_generated=safe_int(job.get("frames_generated"))
        )

    # Check database
    doc = await Database.db["timeline_jobs"].find_one({"job_id": job_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Timeline job not found")

    # Return from DB if not in memory (completed previously)
    return TimelineJobStatus(
        job_id=job_id,
        status=doc.get("status", "queued"),
        progress=100 if doc.get("status") == "completed" else safe_int(doc.get("progress"), 0),
        mesh_url=f"/api/timeline/mesh/{job_id}" if doc.get("status") == "completed" else None,
        error=doc.get("error"),
        total_frames=safe_int(doc.get("total_frames"))
    )


@router.get("/mesh/{job_id}")
async def get_timeline_mesh(job_id: str):
    """Download the generated timeline base mesh GLB."""
    mesh_path = TIMELINE_MESH_DIR / f"{job_id}.glb"

    if not mesh_path.exists():
        raise HTTPException(status_code=404, detail="Timeline mesh not found")

    return FileResponse(
        str(mesh_path),
        media_type="model/gltf-binary",
        filename=f"timeline_{job_id}.glb"
    )


@router.get("/mesh/{job_id}/morphs")
async def get_timeline_morph_data(job_id: str):
    """Download the morph target delta data as JSON."""
    json_path = TIMELINE_MESH_DIR / f"{job_id}.morphs.json"

    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Timeline morph data not found")

    return FileResponse(
        str(json_path),
        media_type="application/json",
        filename=f"timeline_{job_id}.morphs.json"
    )


@router.get("/{patient_id}/{case_id}", response_model=TimelineMetadata)
async def get_timeline_info(patient_id: int, case_id: int):
    """Get timeline metadata for a case - list of scans in chronological order."""
    try:
        # Query all completed NIfTI scans for this case, sorted by scan_timestamp
        cursor = Database.scan_files.find({
            "patient_id": patient_id,
            "case_id": case_id,
            "status": "completed",
            "original_file.file_type": "nifti"  # Only NIfTI files can be morphed
        }).sort("scan_timestamp", 1)  # Ascending = oldest first

        scans = await cursor.to_list(length=None)

        if len(scans) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 2 completed NIfTI scans for timeline. Found {len(scans)}."
            )

        # Check if timeline mesh already exists
        timeline_doc = await Database.db["timeline_jobs"].find_one({
            "patient_id": patient_id,
            "case_id": case_id,
            "status": "completed"
        })

        scan_infos = [
            TimelineScanInfo(
                job_id=s["job_id"],
                scan_timestamp=s["scan_timestamp"],
                original_filename=s["original_file"]["filename"],
                index=i
            ) for i, s in enumerate(scans)
        ]

        return TimelineMetadata(
            patient_id=patient_id,
            case_id=case_id,
            scan_count=len(scans),
            scans=scan_infos,
            has_timeline_mesh=timeline_doc is not None,
            timeline_job_id=timeline_doc["job_id"] if timeline_doc else None,
            timeline_status=timeline_doc["status"] if timeline_doc else None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timeline info: {str(e)}")


@router.post("/{patient_id}/{case_id}/generate", response_model=TimelineJobStatus)
async def generate_timeline(
    patient_id: int,
    case_id: int,
    request: TimelineGenerateRequest,
    background_tasks: BackgroundTasks
):
    """Start async generation of timeline morph-target mesh."""
    try:
        # Verify we have enough scans
        cursor = Database.scan_files.find({
            "patient_id": patient_id,
            "case_id": case_id,
            "status": "completed",
            "original_file.file_type": "nifti"
        }).sort("scan_timestamp", 1)
        scans = await cursor.to_list(length=None)

        if len(scans) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 2 completed NIfTI scans. Found {len(scans)}."
            )

        # Check if timeline already exists and delete old one
        existing = await Database.db["timeline_jobs"].find_one({
            "patient_id": patient_id,
            "case_id": case_id
        })
        if existing:
            # Delete old timeline job and files
            old_job_id = existing["job_id"]
            old_glb = TIMELINE_MESH_DIR / f"{old_job_id}.glb"
            old_json = TIMELINE_MESH_DIR / f"{old_job_id}.morphs.json"
            if old_glb.exists():
                old_glb.unlink()
            if old_json.exists():
                old_json.unlink()
            await Database.db["timeline_jobs"].delete_one({"job_id": old_job_id})

        job_id = str(uuid.uuid4())
        total_frames = (len(scans) - 1) * request.frames_between_scans + len(scans)
        scan_job_ids = [s["job_id"] for s in scans]
        scan_timestamps = [s["scan_timestamp"] for s in scans]

        # Initialize job in memory with all required fields
        timeline_jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "current_step": "Queued for processing...",
            "total_frames": total_frames,
            "frames_generated": 0,
            "mesh_path": None,
            "error": None,
            "patient_id": patient_id,
            "case_id": case_id
        }
        print(f"[Timeline] Created job {job_id} for patient {patient_id}, case {case_id}")

        # Store job in database for persistence
        await Database.db["timeline_jobs"].insert_one({
            "job_id": job_id,
            "patient_id": patient_id,
            "case_id": case_id,
            "status": "queued",
            "frames_between_scans": request.frames_between_scans,
            "total_frames": total_frames,
            "scan_job_ids": scan_job_ids,
            "created_at": datetime.utcnow()
        })

        # Start background processing
        background_tasks.add_task(
            run_timeline_processing,
            job_id, patient_id, case_id,
            scan_job_ids, scan_timestamps,
            request.frames_between_scans
        )

        return TimelineJobStatus(
            job_id=job_id,
            status="queued",
            progress=0,
            current_step="Queued for processing",
            total_frames=total_frames,
            frames_generated=0
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start timeline generation: {str(e)}")
