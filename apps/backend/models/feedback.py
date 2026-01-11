"""Feedback and chat data models for AI-powered case analysis."""
from datetime import datetime
from typing import Optional, Literal, List, Dict, Any
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


class TumorMetrics(BaseModel):
    """Calculated tumor metrics from segmentation data."""
    total_lesion_volume_mm3: Optional[float] = None
    active_enhancing_volume_mm3: Optional[float] = None
    necrotic_core_volume_mm3: Optional[float] = None
    edema_volume_mm3: Optional[float] = None
    midline_shift_mm: Optional[float] = None
    infiltration_index: Optional[float] = None
    has_tumor: bool = False


class ScanSummary(BaseModel):
    """Summary of a single scan for AI context."""
    job_id: str
    filename: str
    scan_date: datetime
    has_tumor: bool = False
    metrics: Optional[TumorMetrics] = None
    regions_detected: List[str] = []


class FeedbackMessageCreate(BaseModel):
    """Schema for creating a new chat message."""
    content: str


class FeedbackMessageInDB(BaseModel):
    """Schema for feedback message in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    message_id: str
    session_id: str
    patient_id: int
    case_id: int
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class FeedbackMessageResponse(BaseModel):
    """Schema for feedback message API response."""
    message_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class FeedbackSessionInDB(BaseModel):
    """Schema for feedback session in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    session_id: str
    patient_id: int
    case_id: int
    summary: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    scan_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class FeedbackSessionResponse(BaseModel):
    """Schema for feedback session API response."""
    session_id: str
    patient_id: int
    case_id: int
    summary: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    scan_count: int = 0
    messages: List[FeedbackMessageResponse] = []
    created_at: datetime
    updated_at: datetime


class GenerateSummaryResponse(BaseModel):
    """Response from generating a new summary."""
    session_id: str
    summary: str
    metrics: Dict[str, Any]
    message: str


class ChatResponse(BaseModel):
    """Response from sending a chat message."""
    user_message: FeedbackMessageResponse
    assistant_message: FeedbackMessageResponse
