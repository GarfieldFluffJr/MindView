"""Patient management API endpoints."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import DuplicateKeyError

from database import Database
from models.patient import PatientCreate, PatientUpdate, PatientResponse

router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(patient: PatientCreate):
    """Create a new patient."""
    try:
        # Create patient document
        patient_doc = {
            **patient.model_dump(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await Database.patients.insert_one(patient_doc)

        # Retrieve and return the created patient
        created_patient = await Database.patients.find_one({"_id": result.inserted_id})

        return PatientResponse(**created_patient)

    except DuplicateKeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Patient with ID '{patient.patient_id}' already exists",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create patient: {str(e)}")


@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search by patient_id, first_name, or last_name"),
):
    """List all patients with pagination and optional search."""
    try:
        # Build query filter
        query = {}
        if search:
            query = {
                "$or": [
                    {"patient_id": {"$regex": search, "$options": "i"}},
                    {"first_name": {"$regex": search, "$options": "i"}},
                    {"last_name": {"$regex": search, "$options": "i"}},
                ]
            }

        # Query patients
        cursor = Database.patients.find(query).skip(skip).limit(limit).sort("created_at", -1)
        patients = await cursor.to_list(length=limit)

        return [PatientResponse(**patient) for patient in patients]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list patients: {str(e)}")


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str):
    """Get a single patient by ID."""
    try:
        patient = await Database.patients.find_one({"patient_id": patient_id})

        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

        return PatientResponse(**patient)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patient: {str(e)}")


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, patient_update: PatientUpdate):
    """Update patient information."""
    try:
        # Build update document (only include fields that were provided)
        update_data = {
            k: v for k, v in patient_update.model_dump(exclude_unset=True).items() if v is not None
        }

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_data["updated_at"] = datetime.utcnow()

        # Update the patient
        result = await Database.patients.update_one(
            {"patient_id": patient_id}, {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

        # Retrieve and return updated patient
        updated_patient = await Database.patients.find_one({"patient_id": patient_id})
        return PatientResponse(**updated_patient)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update patient: {str(e)}")


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(patient_id: str):
    """Delete a patient."""
    try:
        # Check if patient has any medical cases
        case_count = await Database.medical_cases.count_documents({"patient_id": patient_id})
        if case_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete patient with {case_count} existing medical cases. Delete cases first.",
            )

        # Delete the patient
        result = await Database.patients.delete_one({"patient_id": patient_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete patient: {str(e)}")
