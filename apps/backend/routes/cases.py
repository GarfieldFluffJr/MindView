"""Medical case management API endpoints."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import DuplicateKeyError

from database import Database
from models.medical_case import MedicalCaseCreate, MedicalCaseUpdate, MedicalCaseResponse

router = APIRouter()


@router.post("/", response_model=MedicalCaseResponse, status_code=201)
async def create_case(case: MedicalCaseCreate):
    """Create a new medical case."""
    try:
        # Verify patient exists
        patient = await Database.patients.find_one({"patient_id": case.patient_id})
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=f"Patient '{case.patient_id}' not found. Create patient first.",
            )

        # Create case document
        case_doc = {
            **case.model_dump(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await Database.medical_cases.insert_one(case_doc)

        # Retrieve and return the created case
        created_case = await Database.medical_cases.find_one({"_id": result.inserted_id})

        return MedicalCaseResponse(**created_case)

    except HTTPException:
        raise
    except DuplicateKeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Case with ID '{case.case_id}' already exists",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")


@router.get("/", response_model=List[MedicalCaseResponse])
async def list_cases(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    status: Optional[str] = Query(None, description="Filter by status (active/closed/archived)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
):
    """List medical cases with optional filters and pagination."""
    try:
        # Build query filter
        query = {}
        if patient_id:
            query["patient_id"] = patient_id
        if status:
            query["status"] = status

        # Query cases
        cursor = (
            Database.medical_cases.find(query)
            .skip(skip)
            .limit(limit)
            .sort("created_at", -1)
        )
        cases = await cursor.to_list(length=limit)

        return [MedicalCaseResponse(**case) for case in cases]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list cases: {str(e)}")


@router.get("/{case_id}", response_model=MedicalCaseResponse)
async def get_case(case_id: str):
    """Get a single medical case by ID."""
    try:
        case = await Database.medical_cases.find_one({"case_id": case_id})

        if not case:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

        return MedicalCaseResponse(**case)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get case: {str(e)}")


@router.get("/{case_id}/files")
async def get_case_files(case_id: str):
    """Get all scan files associated with a case."""
    try:
        # Verify case exists
        case = await Database.medical_cases.find_one({"case_id": case_id})
        if not case:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

        # Get all files for this case
        cursor = Database.scan_files.find({"case_id": case_id}).sort("scan_timestamp", -1)
        files = await cursor.to_list(length=None)

        return {
            "case_id": case_id,
            "patient_id": case["patient_id"],
            "file_count": len(files),
            "files": files,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get case files: {str(e)}")


@router.put("/{case_id}", response_model=MedicalCaseResponse)
async def update_case(case_id: str, case_update: MedicalCaseUpdate):
    """Update medical case information."""
    try:
        # Build update document (only include fields that were provided)
        update_data = {
            k: v for k, v in case_update.model_dump(exclude_unset=True).items() if v is not None
        }

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_data["updated_at"] = datetime.utcnow()

        # Update the case
        result = await Database.medical_cases.update_one(
            {"case_id": case_id}, {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

        # Retrieve and return updated case
        updated_case = await Database.medical_cases.find_one({"case_id": case_id})
        return MedicalCaseResponse(**updated_case)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update case: {str(e)}")


@router.delete("/{case_id}", status_code=204)
async def delete_case(case_id: str):
    """Delete a medical case."""
    try:
        # Check if case has any scan files
        file_count = await Database.scan_files.count_documents({"case_id": case_id})
        if file_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete case with {file_count} existing scan files. Delete files first.",
            )

        # Delete the case
        result = await Database.medical_cases.delete_one({"case_id": case_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete case: {str(e)}")
