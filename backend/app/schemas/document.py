"""Document & upload Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Upload ───────────────────────────────────────────────
class InitUploadRequest(BaseModel):
    filename: str
    file_size: Optional[int] = None
    total_parts: Optional[int] = None


class InitUploadResponse(BaseModel):
    upload_id: str
    doc_id: str


class CompleteUploadResponse(BaseModel):
    upload_id: str
    doc_id: str
    status: str


# ── Document ─────────────────────────────────────────────
class DocumentOut(BaseModel):
    doc_id: str
    filename: str
    file_size: Optional[int] = None
    mime_type: str = "application/pdf"
    page_count: Optional[int] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentVersionOut(BaseModel):
    version_id: str
    doc_id: str
    version_no: int
    status: str
    parse_params: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
