"""Export endpoints.

POST /api/v1/exports             – create export task
GET  /api/v1/exports/{export_id} – export status & download link
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.models import DocumentVersion, ExportTask
from app.schemas.common import ApiResponse
from app.schemas.export import CreateExportRequest, ExportOut
from app.services.storage import LocalFSAdapter
from app.utils.ulid import generate_ulid

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post("", response_model=ApiResponse[ExportOut])
def create_export(
    body: CreateExportRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an export task (idempotent via idempotency_key)."""
    if body.idempotency_key:
        existing = db.query(ExportTask).filter_by(idempotency_key=body.idempotency_key).first()
        if existing:
            return ApiResponse(data=ExportOut.model_validate(existing))

    version = (
        db.query(DocumentVersion)
        .filter_by(version_id=body.version_id, tenant_id=user.tenant_id)
        .first()
    )
    if not version:
        raise HTTPException(404, "Version not found")

    export = ExportTask(
        export_id=generate_ulid("exp"),
        tenant_id=user.tenant_id,
        version_id=body.version_id,
        format=body.format,
        idempotency_key=body.idempotency_key,
        created_by=user.user_id,
    )
    db.add(export)
    db.commit()

    # Dispatch export task
    from app.tasks.export import render_docx_pdf

    render_docx_pdf.delay(export_id=export.export_id)

    return ApiResponse(data=ExportOut.model_validate(export))


@router.get("/{export_id}", response_model=ApiResponse[ExportOut])
def get_export(
    export_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    export = db.query(ExportTask).filter_by(export_id=export_id, tenant_id=user.tenant_id).first()
    if not export:
        raise HTTPException(404, "Export not found")
    return ApiResponse(data=ExportOut.model_validate(export))


@router.get("/{export_id}/download")
def download_export(
    export_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    export = db.query(ExportTask).filter_by(export_id=export_id, tenant_id=user.tenant_id).first()
    if not export:
        raise HTTPException(404, "Export not found")
    if export.status != "done" or not export.file_path:
        raise HTTPException(400, "Export not ready")

    storage = LocalFSAdapter()
    abs_path = storage.abs_path(export.file_path)
    media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if export.file_path.endswith(".pdf"):
        media = "application/pdf"
    return FileResponse(abs_path, media_type=media, filename=f"report.{export.format}")
