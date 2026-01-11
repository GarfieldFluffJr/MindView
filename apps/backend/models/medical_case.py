"""Medical case data models."""
from datetime import datetime
from typing import Optional, Literal
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


class MedicalCaseCreate(BaseModel):
    """Schema for creating a new medical case."""

    patient_id: int = Field(..., description="Patient this case belongs to")
    case_name: str = Field(..., description="Name/title of the case")
    diagnosis: Optional[str] = None
    doctor_notes: Optional[str] = None
    created_by: Optional[str] = None
    status: Literal["active", "closed", "archived"] = "active"
    metadata: Optional[dict] = {}


class MedicalCaseUpdate(BaseModel):
    """Schema for updating a medical case."""

    case_name: Optional[str] = None
    diagnosis: Optional[str] = None
    doctor_notes: Optional[str] = None
    status: Optional[Literal["active", "closed", "archived"]] = None
    metadata: Optional[dict] = None


class MedicalCaseInDB(BaseModel):
    """Schema for medical case document in database."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    case_id: int
    patient_id: int
    case_name: str
    diagnosis: Optional[str] = None
    doctor_notes: Optional[str] = None
    created_by: Optional[str] = None
    status: Literal["active", "closed", "archived"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = {}

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class MedicalCaseResponse(BaseModel):
    """Schema for medical case API response."""

    case_id: int
    patient_id: int
    case_name: str
    diagnosis: Optional[str] = None
    doctor_notes: Optional[str] = None
    created_by: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: dict = {}


class MedicalCaseWithStats(MedicalCaseResponse):
    """Schema for medical case API response with additional statistics."""

    file_count: int = 0
