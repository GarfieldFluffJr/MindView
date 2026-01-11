"""Timeline data models for morph target generation."""
from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from bson import ObjectId


class TimelineScanInfo(BaseModel):
    """Info about a single scan in the timeline."""

    job_id: str
    scan_timestamp: datetime
    original_filename: str
    index: int  # Position in chronological order


class TimelineMetadata(BaseModel):
    """Response for timeline info endpoint."""

    patient_id: int
    case_id: int
    scan_count: int
    scans: List[TimelineScanInfo]
    has_timeline_mesh: bool
    timeline_job_id: Optional[str] = None
    timeline_status: Optional[str] = None


class TimelineGenerateRequest(BaseModel):
    """Request to generate timeline morph mesh."""

    frames_between_scans: int = Field(default=10, ge=1, le=30)


class TimelineJobStatus(BaseModel):
    """Status of timeline generation job."""

    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int = Field(default=0, ge=0, le=100)
    current_step: Optional[str] = None
    mesh_url: Optional[str] = None
    error: Optional[str] = None
    total_frames: Optional[int] = None
    frames_generated: Optional[int] = None


class TimelineJobInDB(BaseModel):
    """Schema for timeline job document in database."""

    job_id: str
    patient_id: int
    case_id: int
    status: Literal["queued", "processing", "completed", "failed"] = "queued"
    progress: int = 0
    current_step: Optional[str] = None
    frames_between_scans: int = 10
    total_frames: Optional[int] = None
    frames_generated: int = 0
    scan_job_ids: List[str] = []
    mesh_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
