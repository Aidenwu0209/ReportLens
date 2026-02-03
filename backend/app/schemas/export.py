"""Export task Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CreateExportRequest(BaseModel):
    version_id: str
    format: str = "docx"  # docx / pdf
    idempotency_key: Optional[str] = None


class ExportOut(BaseModel):
    export_id: str
    version_id: str
    format: str
    status: str
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
