"""Patient data models."""
from datetime import datetime
from typing import Optional
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


class PatientCreate(BaseModel):
    """Schema for creating a new patient."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    medical_record_number: Optional[str] = None
    metadata: Optional[dict] = {}


class PatientUpdate(BaseModel):
    """Schema for updating patient information."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    medical_record_number: Optional[str] = None
    metadata: Optional[dict] = None


class PatientInDB(BaseModel):
    """Schema for patient document in database."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    patient_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    medical_record_number: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = {}

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PatientResponse(BaseModel):
    """Schema for patient API response."""

    patient_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    medical_record_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: dict = {}


class PatientWithStats(BaseModel):
    """Schema for patient with statistics."""

    patient_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    medical_record_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: dict = {}
    case_count: int = 0
    file_count: int = 0
