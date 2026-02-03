"""Q&A / Chat endpoints.

POST /api/v1/qa/sessions                     – create session
GET  /api/v1/qa/sessions/{sid}               – get session
POST /api/v1/qa/sessions/{sid}/messages      – send question
GET  /api/v1/qa/sessions/{sid}/messages      – list messages
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.models import ChatMessage, ChatSession, DocumentVersion
from app.schemas.chat import (
    ChatMessageOut,
    CreateSessionRequest,
    SendMessageRequest,
    SessionOut,
)
from app.schemas.common import ApiResponse
from app.utils.ulid import generate_ulid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/sessions", response_model=ApiResponse[SessionOut])
def create_session(
    body: CreateSessionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    version = (
        db.query(DocumentVersion)
        .filter_by(version_id=body.version_id, tenant_id=user.tenant_id)
        .first()
    )
    if not version:
        raise HTTPException(404, "Version not found")

    session = ChatSession(
        session_id=generate_ulid("css"),
        tenant_id=user.tenant_id,
        version_id=body.version_id,
        created_by=user.user_id,
        title=body.title or "新对话",
    )
    db.add(session)
    db.commit()
    return ApiResponse(data=SessionOut.model_validate(session))


@router.get("/sessions/{sid}", response_model=ApiResponse[SessionOut])
def get_session(
    sid: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter_by(session_id=sid, tenant_id=user.tenant_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return ApiResponse(data=SessionOut.model_validate(session))


@router.post("/sessions/{sid}/messages", response_model=ApiResponse[ChatMessageOut])
def send_message(
    sid: str,
    body: SendMessageRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a user question and get AI response (with evidence refs)."""
    session = db.query(ChatSession).filter_by(session_id=sid, tenant_id=user.tenant_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    # Idempotency
    if body.idempotency_key:
        existing = db.query(ChatMessage).filter_by(idempotency_key=body.idempotency_key).first()
        if existing:
            return ApiResponse(data=ChatMessageOut.model_validate(existing))

    # Save user message
    user_msg = ChatMessage(
        message_id=generate_ulid("msg"),
        session_id=sid,
        tenant_id=user.tenant_id,
        role="user",
        content=body.content,
        idempotency_key=body.idempotency_key,
    )
    db.add(user_msg)
    db.flush()

    # Generate AI response (simplified – calls Wenxin for Q&A)
    try:
        from app.adapters.wenxin_llm import generate_insights

        loop = asyncio.new_event_loop()
        output = loop.run_until_complete(
            generate_insights(
                metrics_json="{}",
                chunks_text=body.content,
                prompt_version="qa_v1",
            )
        )
        loop.close()

        answer_content = output.summary or "暂无回答"
        evidence = [
            {"page_no": e.page_no, "bbox_norm": e.bbox_norm, "snippet": e.snippet}
            for e in output.evidence_refs
        ]
    except Exception as exc:
        logger.warning("Q&A LLM call failed: %s", exc)
        answer_content = "抱歉，暂时无法生成回答，请稍后重试。"
        evidence = []

    assistant_msg = ChatMessage(
        message_id=generate_ulid("msg"),
        session_id=sid,
        tenant_id=user.tenant_id,
        role="assistant",
        content=answer_content,
        evidence_refs=evidence if evidence else None,
    )
    db.add(assistant_msg)
    db.commit()

    return ApiResponse(data=ChatMessageOut.model_validate(assistant_msg))


@router.get("/sessions/{sid}/messages")
def list_messages(
    sid: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter_by(session_id=sid, tenant_id=user.tenant_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    msgs = (
        db.query(ChatMessage)
        .filter_by(session_id=sid)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return ApiResponse(data=[ChatMessageOut.model_validate(m) for m in msgs])
