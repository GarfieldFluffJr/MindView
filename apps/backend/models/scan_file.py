"""Scan file data models."""
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


class OriginalFileInfo(BaseModel):
    """Information about the original uploaded file."""

    gridfs_id: Optional[PyObjectId] = None
    filename: str
    content_type: str
    size_bytes: int
    file_type: Literal["nifti", "obj"]


class ProcessedMeshInfo(BaseModel):
    """Information about the processed mesh file."""

    gridfs_id: Optional[PyObjectId] = None
    filename: str
    content_type: str = "model/gltf-binary"
    size_bytes: Optional[int] = None
    processing_time_seconds: Optional[float] = None


class ScanFileCreate(BaseModel):
    """Schema for creating a new scan file record."""

    patient_id: str
    case_id: str
    scan_timestamp: Optional[datetime] = None
    doctor_notes: Optional[str] = None
    metadata: Optional[dict] = {}


class ScanFileInDB(BaseModel):
    """Schema for scan file document in database."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    file_id: str
    job_id: str
    case_id: str
    patient_id: str
    original_file: OriginalFileInfo
    processed_mesh: Optional[ProcessedMeshInfo] = None
    status: Literal["queued", "processing", "completed", "failed"] = "queued"
    progress: int = 0
    error: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    scan_timestamp: datetime = Field(default_factory=datetime.utcnow)
    doctor_notes: Optional[str] = None
    metadata: dict = {}

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ScanFileResponse(BaseModel):
    """Schema for scan file API response."""

    job_id: str
    file_id: str
    case_id: str
    patient_id: str
    status: str
    progress: int
    mesh_url: Optional[str] = None
    original_url: Optional[str] = None
    error: Optional[str] = None
    uploaded_at: datetime
    scan_timestamp: datetime
    doctor_notes: Optional[str] = None
    metadata: dict = {}
