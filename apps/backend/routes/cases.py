"""Medical case management API endpoints."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import DuplicateKeyError

from database import Database
from models.medical_case import MedicalCaseCreate, MedicalCaseUpdate, MedicalCaseResponse, MedicalCaseWithStats

router = APIRouter()


@router.post("/", response_model=MedicalCaseWithStats, status_code=201)
async def create_case(case: MedicalCaseCreate):
    """Create a new medical case with auto-generated case_id."""
    try:
        # Verify patient exists
        patient = await Database.patients.find_one({"patient_id": case.patient_id})
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=f"Patient '{case.patient_id}' not found. Create patient first.",
            )

        # Find the highest case_id for this patient and increment by 1
        last_case = await Database.medical_cases.find_one(
            {"patient_id": case.patient_id},
            sort=[("case_id", -1)]
        )
        next_case_id = 0 if last_case is None else last_case["case_id"] + 1

        # Create case document
        case_doc = {
            **case.model_dump(),
            "case_id": next_case_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await Database.medical_cases.insert_one(case_doc)

        # Retrieve and return the created case with file_count = 0
        created_case = await Database.medical_cases.find_one({"_id": result.inserted_id})

        return MedicalCaseWithStats(**created_case, file_count=0)

    except HTTPException:
        raise
    except DuplicateKeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Case with ID '{next_case_id}' already exists for patient {case.patient_id}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")


@router.get("/", response_model=List[MedicalCaseWithStats])
async def list_cases(
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    status: Optional[str] = Query(None, description="Filter by status (active/closed/archived)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
):
    """List medical cases with optional filters and pagination, including file counts."""
    try:
        # Build query filter
        query = {}
        if patient_id is not None:
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

        # Add file counts for each case
        cases_with_stats = []
        for case in cases:
            file_count = await Database.scan_files.count_documents({
                "patient_id": case["patient_id"],
                "case_id": case["case_id"]
            })
            cases_with_stats.append(MedicalCaseWithStats(**case, file_count=file_count))

        return cases_with_stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list cases: {str(e)}")


@router.get("/{patient_id}/{case_id}", response_model=MedicalCaseResponse)
async def get_case(patient_id: int, case_id: int):
    """Get a single medical case by patient ID and case ID."""
    try:
        case = await Database.medical_cases.find_one({
            "patient_id": patient_id,
            "case_id": case_id
        })

        if not case:
            raise HTTPException(
                status_code=404,
                detail=f"Case '{case_id}' not found for patient {patient_id}"
            )

        return MedicalCaseResponse(**case)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get case: {str(e)}")


@router.get("/{patient_id}/{case_id}/files")
async def get_case_files(patient_id: int, case_id: int):
    """Get all scan files associated with a case."""
    try:
        # Verify case exists
        case = await Database.medical_cases.find_one({
            "patient_id": patient_id,
            "case_id": case_id
        })
        if not case:
            raise HTTPException(
                status_code=404,
                detail=f"Case '{case_id}' not found for patient {patient_id}"
            )

        # Get all files for this case
        cursor = Database.scan_files.find({
            "patient_id": patient_id,
            "case_id": case_id
        }).sort("scan_timestamp", -1)
        files = await cursor.to_list(length=None)

        return {
            "case_id": case_id,
            "patient_id": patient_id,
            "file_count": len(files),
            "files": files,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get case files: {str(e)}")


@router.put("/{patient_id}/{case_id}", response_model=MedicalCaseResponse)
async def update_case(patient_id: int, case_id: int, case_update: MedicalCaseUpdate):
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
            {"patient_id": patient_id, "case_id": case_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Case '{case_id}' not found for patient {patient_id}"
            )

        # Retrieve and return updated case
        updated_case = await Database.medical_cases.find_one({
            "patient_id": patient_id,
            "case_id": case_id
        })
        return MedicalCaseResponse(**updated_case)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update case: {str(e)}")


@router.delete("/{patient_id}/{case_id}", status_code=204)
async def delete_case(
    patient_id: int,
    case_id: int,
    force: bool = Query(False, description="Force delete case along with all scan files")
):
    """Delete a medical case and optionally all associated files."""
    try:
        # Check if case exists
        case = await Database.medical_cases.find_one({
            "patient_id": patient_id,
            "case_id": case_id
        })
        if not case:
            raise HTTPException(
                status_code=404,
                detail=f"Case '{case_id}' not found for patient {patient_id}"
            )

        if force:
            # Delete all associated scan files
            await Database.scan_files.delete_many({
                "patient_id": patient_id,
                "case_id": case_id
            })
        else:
            # Check if case has any scan files
            file_count = await Database.scan_files.count_documents({
                "patient_id": patient_id,
                "case_id": case_id
            })
            if file_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete case with {file_count} existing scan files. Use force=true to delete all data.",
                )

        # Delete the case
        result = await Database.medical_cases.delete_one({
            "patient_id": patient_id,
            "case_id": case_id
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Case '{case_id}' not found for patient {patient_id}"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete case: {str(e)}")
