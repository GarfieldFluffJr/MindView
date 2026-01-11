"""Collaborative notes API endpoints."""
import uuid
import hashlib
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException

from database import Database
from models.note import NoteCreate, NoteResponse

router = APIRouter()

# Color palette for note blurbs
NOTE_COLORS = [
    "#FFB3BA",  # Light pink
    "#BAFFC9",  # Light green
    "#BAE1FF",  # Light blue
    "#FFFFBA",  # Light yellow
    "#FFD4BA",  # Light orange
    "#E0BBE4",  # Light purple
    "#C4FAF8",  # Light cyan
    "#FFC6FF",  # Light magenta
]


def get_color_for_doctor(doctor_name: str) -> str:
    """Get a consistent color for a doctor based on their name."""
    hash_value = int(hashlib.md5(doctor_name.encode()).hexdigest(), 16)
    color_index = hash_value % len(NOTE_COLORS)
    return NOTE_COLORS[color_index]


@router.get("/{patient_id}/{case_id}/{file_id}", response_model=List[NoteResponse])
async def get_notes_for_file(patient_id: int, case_id: int, file_id: str):
    """Get all notes for a specific file."""
    try:
        cursor = Database.notes.find({
            "patient_id": patient_id,
            "case_id": case_id,
            "file_id": file_id
        }).sort("created_at", -1)

        notes = await cursor.to_list(length=None)

        return [
            NoteResponse(
                note_id=note["note_id"],
                file_id=note["file_id"],
                patient_id=note["patient_id"],
                case_id=note["case_id"],
                content=note["content"],
                doctor_name=note["doctor_name"],
                color=note["color"],
                created_at=note["created_at"]
            )
            for note in notes
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get notes: {str(e)}")


@router.post("/{patient_id}/{case_id}/{file_id}", response_model=NoteResponse)
async def create_note(
    patient_id: int,
    case_id: int,
    file_id: str,
    note_data: NoteCreate
):
    """Create a new note for a file."""
    try:
        # Verify the file exists
        file_doc = await Database.scan_files.find_one({
            "patient_id": patient_id,
            "case_id": case_id,
            "file_id": file_id
        })

        if not file_doc:
            raise HTTPException(
                status_code=404,
                detail=f"File '{file_id}' not found"
            )

        note_id = str(uuid.uuid4())
        color = get_color_for_doctor(note_data.doctor_name)

        note_doc = {
            "note_id": note_id,
            "file_id": file_id,
            "patient_id": patient_id,
            "case_id": case_id,
            "content": note_data.content,
            "doctor_name": note_data.doctor_name,
            "color": color,
            "created_at": datetime.utcnow()
        }

        await Database.notes.insert_one(note_doc)

        return NoteResponse(
            note_id=note_id,
            file_id=file_id,
            patient_id=patient_id,
            case_id=case_id,
            content=note_data.content,
            doctor_name=note_data.doctor_name,
            color=color,
            created_at=note_doc["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create note: {str(e)}")


@router.delete("/{patient_id}/{case_id}/{file_id}/{note_id}", status_code=204)
async def delete_note(patient_id: int, case_id: int, file_id: str, note_id: str):
    """Delete a note."""
    try:
        result = await Database.notes.delete_one({
            "patient_id": patient_id,
            "case_id": case_id,
            "file_id": file_id,
            "note_id": note_id
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Note '{note_id}' not found"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete note: {str(e)}")
