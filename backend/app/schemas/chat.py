"""Q&A / chat Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    version_id: str
    title: Optional[str] = None


class SessionOut(BaseModel):
    session_id: str
    version_id: str
    title: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str
    idempotency_key: Optional[str] = None


class ChatMessageOut(BaseModel):
    message_id: str
    role: str
    content: Optional[str] = None
    evidence_refs: Optional[list] = None
    created_at: datetime

    model_config = {"from_attributes": True}
