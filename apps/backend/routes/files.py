"""Scan file management API endpoints."""
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

from database import Database
from models.scan_file import ScanFileResponse
from services.gridfs_service import delete_from_gridfs

router = APIRouter()

# Path to mesh storage
MESH_DIR = Path(__file__).parent.parent / "storage" / "meshes"


@router.get("/{patient_id}/{case_id}", response_model=List[ScanFileResponse])
async def list_files(patient_id: int, case_id: int):
    """List all scan files for a case."""
    try:
        # Query files for this case
        cursor = Database.scan_files.find({
            "patient_id": patient_id,
            "case_id": case_id
        }).sort("uploaded_at", -1)

        files = await cursor.to_list(length=None)

        # Convert to response format, filtering out orphaned files
        result = []
        orphaned_ids = []

        for file_doc in files:
            job_id = file_doc["job_id"]
            status = file_doc["status"]

            # Check if completed files have their mesh (in GridFS or on disk)
            if status == "completed":
                processed_mesh = file_doc.get("processed_mesh")
                has_mesh_in_gridfs = processed_mesh and processed_mesh.get("gridfs_id")
                has_mesh_on_disk = (MESH_DIR / f"{job_id}.glb").exists()

                # Only mark as orphaned if mesh is missing from both GridFS and disk
                if not has_mesh_in_gridfs and not has_mesh_on_disk:
                    # Mark for cleanup
                    orphaned_ids.append(job_id)
                    continue

            result.append(ScanFileResponse(
                job_id=job_id,
                file_id=file_doc["file_id"],
                case_id=file_doc["case_id"],
                patient_id=file_doc["patient_id"],
                original_filename=file_doc["original_file"]["filename"],
                status=status,
                progress=file_doc["progress"],
                mesh_url=f"/api/mesh/{job_id}" if status == "completed" else None,
                original_url=None,
                error=file_doc.get("error"),
                uploaded_at=file_doc["uploaded_at"],
                scan_timestamp=file_doc["scan_timestamp"],
                doctor_notes=file_doc.get("doctor_notes"),
                metadata=file_doc.get("metadata", {})
            ))

        # Clean up orphaned records in background
        if orphaned_ids:
            for job_id in orphaned_ids:
                await Database.scan_files.delete_one({"job_id": job_id})
                await Database.notes.delete_many({"file_id": job_id})

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.delete("/{patient_id}/{case_id}/{job_id}", status_code=204)
async def delete_file(patient_id: int, case_id: int, job_id: str):
    """Delete a scan file from GridFS and database."""
    try:
        # Find the file
        file_doc = await Database.scan_files.find_one({
            "patient_id": patient_id,
            "case_id": case_id,
            "job_id": job_id
        })

        if not file_doc:
            raise HTTPException(
                status_code=404,
                detail=f"File '{job_id}' not found for case {case_id} and patient {patient_id}"
            )

        # Delete original file from GridFS if it exists
        original_file = file_doc.get("original_file", {})
        if original_file.get("gridfs_id"):
            try:
                await delete_from_gridfs(ObjectId(original_file["gridfs_id"]))
                print(f"Deleted original file from GridFS: {original_file['gridfs_id']}")
            except Exception as e:
                print(f"Warning: Failed to delete original file from GridFS: {e}")

        # Delete processed mesh from GridFS if it exists
        processed_mesh = file_doc.get("processed_mesh", {})
        if processed_mesh and processed_mesh.get("gridfs_id"):
            try:
                await delete_from_gridfs(ObjectId(processed_mesh["gridfs_id"]))
                print(f"Deleted mesh from GridFS: {processed_mesh['gridfs_id']}")
            except Exception as e:
                print(f"Warning: Failed to delete mesh from GridFS: {e}")

        # Also delete from filesystem if it exists (for backward compatibility)
        mesh_path = MESH_DIR / f"{job_id}.glb"
        if mesh_path.exists():
            mesh_path.unlink()
            print(f"Deleted mesh from filesystem: {mesh_path}")

        # Delete associated notes
        await Database.notes.delete_many({"file_id": job_id})

        # Delete the document from database
        result = await Database.scan_files.delete_one({
            "patient_id": patient_id,
            "case_id": case_id,
            "job_id": job_id
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"File '{job_id}' not found"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
