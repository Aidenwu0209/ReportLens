"""Job-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CreateJobRequest(BaseModel):
    version_id: str
    idempotency_key: Optional[str] = None


class JobOut(BaseModel):
    job_id: str
    version_id: str
    doc_id: str
    stage: str
    progress: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobEventData(BaseModel):
    """Payload sent over SSE."""
    job_id: str
    stage: str
    progress: int
    message: Optional[str] = None
