"""Collaborative note data models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _):
        return {"type": "string"}


class NoteCreate(BaseModel):
    """Schema for creating a new note."""
    content: str
    doctor_name: str = "Dr. Smith"


class NoteInDB(BaseModel):
    """Schema for note document in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    note_id: str
    file_id: str
    patient_id: int
    case_id: int
    content: str
    doctor_name: str
    color: str  # Hex color for the note blurb
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class NoteResponse(BaseModel):
    """Schema for note API response."""
    note_id: str
    file_id: str
    patient_id: int
    case_id: int
    content: str
    doctor_name: str
    color: str
    created_at: datetime
