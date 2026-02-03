"""Job endpoints.

POST  /api/v1/jobs                – start parsing task
GET   /api/v1/jobs/{job_id}       – job status
GET   /api/v1/jobs/{job_id}/events – SSE progress stream
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.database import SessionLocal, get_db
from app.core.security import CurrentUser, get_current_user
from app.models.models import DocumentVersion, Job
from app.schemas.common import ApiResponse
from app.schemas.job import CreateJobRequest, JobOut
from app.utils.ulid import generate_ulid

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ── POST /jobs ───────────────────────────────────────────
@router.post("", response_model=ApiResponse[JobOut])
def create_job(
    body: CreateJobRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """T5 – Start a parsing job (with idempotency key support)."""
    # Idempotency check
    if body.idempotency_key:
        existing = db.query(Job).filter_by(idempotency_key=body.idempotency_key).first()
        if existing:
            return ApiResponse(data=JobOut.model_validate(existing))

    version = (
        db.query(DocumentVersion)
        .filter_by(version_id=body.version_id, tenant_id=user.tenant_id)
        .first()
    )
    if not version:
        raise HTTPException(404, "Version not found")

    job = Job(
        job_id=generate_ulid("job"),
        tenant_id=user.tenant_id,
        version_id=version.version_id,
        doc_id=version.doc_id,
        stage="queued",
        idempotency_key=body.idempotency_key,
    )
    db.add(job)
    db.commit()

    # Dispatch Celery pipeline
    from app.tasks.pipeline import run_job

    run_job.delay(job_id=job.job_id, doc_id=version.doc_id, version_id=version.version_id)

    return ApiResponse(data=JobOut.model_validate(job))


# ── GET /jobs/{job_id} ───────────────────────────────────
@router.get("/{job_id}", response_model=ApiResponse[JobOut])
def get_job(
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter_by(job_id=job_id, tenant_id=user.tenant_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return ApiResponse(data=JobOut.model_validate(job))


# ── GET /jobs/{job_id}/events  (T6 – SSE) ───────────────
@router.get("/{job_id}/events")
async def job_events(
    job_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """T6 – Server-Sent Events stream for real-time job progress."""

    async def event_generator() -> AsyncGenerator[dict, None]:
        last_stage = ""
        last_progress = -1

        while True:
            if await request.is_disconnected():
                break

            db = SessionLocal()
            try:
                job = db.query(Job).filter_by(job_id=job_id, tenant_id=user.tenant_id).first()
                if not job:
                    yield {"event": "error", "data": json.dumps({"message": "Job not found"})}
                    break

                if job.stage != last_stage or job.progress != last_progress:
                    last_stage = job.stage
                    last_progress = job.progress
                    yield {
                        "event": "progress",
                        "data": json.dumps({
                            "job_id": job.job_id,
                            "stage": job.stage,
                            "progress": job.progress,
                            "message": f"Stage: {job.stage}, Progress: {job.progress}%",
                        }),
                    }

                if job.stage in ("done", "failed"):
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "job_id": job.job_id,
                            "stage": job.stage,
                            "progress": job.progress,
                            "error": job.error_message,
                        }),
                    }
                    break
            finally:
                db.close()

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
