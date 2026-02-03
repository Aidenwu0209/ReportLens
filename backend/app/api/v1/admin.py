"""Admin console endpoints (DLQ replay, audit logs).

GET  /api/v1/admin/audit-logs  – list audit logs
POST /api/v1/admin/jobs/{job_id}/replay  – replay failed job (DLQ)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.models import AuditLog, Job
from app.schemas.common import ApiResponse
from app.utils.ulid import generate_ulid

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs")
def list_audit_logs(
    page: int = 1,
    page_size: int = 20,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit logs for the tenant (admin only)."""
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")

    offset = (page - 1) * page_size
    logs = (
        db.query(AuditLog)
        .filter_by(tenant_id=user.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return ApiResponse(
        data=[
            {
                "log_id": log.log_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "user_id": log.user_id,
                "detail": log.detail,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    )


@router.post("/jobs/{job_id}/replay")
def replay_job(
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """DLQ replay – re-queue a failed job."""
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")

    job = db.query(Job).filter_by(job_id=job_id, tenant_id=user.tenant_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.stage != "failed":
        raise HTTPException(400, "Only failed jobs can be replayed")

    job.stage = "queued"
    job.progress = 0
    job.error_message = None
    job.retry_count += 1
    db.commit()

    # Log audit
    audit = AuditLog(
        log_id=generate_ulid("aud"),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        action="job_replay",
        resource_type="job",
        resource_id=job_id,
    )
    db.add(audit)
    db.commit()

    # Re-dispatch
    from app.tasks.pipeline import run_job

    run_job.delay(job_id=job.job_id, doc_id=job.doc_id, version_id=job.version_id)

    return ApiResponse(data={"job_id": job_id, "status": "replayed"})
