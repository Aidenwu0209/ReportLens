"""Document & upload endpoints.

POST  /api/v1/documents/init         – initialise upload (returns upload_id + doc_id)
PUT   /api/v1/uploads/{upload_id}/parts/{part_no}  – chunked upload
POST  /api/v1/uploads/{upload_id}/complete          – merge chunks
GET   /api/v1/documents/{doc_id}                     – document detail
GET   /api/v1/documents/{doc_id}/versions/{ver_id}/pages/{page_no}  – page image
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.models import Document, DocumentVersion, Upload, UploadPart
from app.schemas.common import ApiResponse
from app.schemas.document import (
    CompleteUploadResponse,
    DocumentOut,
    DocumentVersionOut,
    InitUploadRequest,
    InitUploadResponse,
)
from app.services.storage import LocalFSAdapter, StoragePaths
from app.utils.ulid import generate_ulid

router = APIRouter(tags=["documents"])


# ── POST /documents/init ─────────────────────────────────
@router.post("/documents/init", response_model=ApiResponse[InitUploadResponse])
def init_upload(
    body: InitUploadRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """T4 – Initialise a chunked upload session."""
    doc = Document(
        doc_id=generate_ulid("doc"),
        tenant_id=user.tenant_id,
        filename=body.filename,
        file_size=body.file_size,
        created_by=user.user_id,
    )
    db.add(doc)
    db.flush()

    upload = Upload(
        upload_id=generate_ulid("upl"),
        tenant_id=user.tenant_id,
        doc_id=doc.doc_id,
        filename=body.filename,
        total_parts=body.total_parts,
        file_size=body.file_size,
        status="initiated",
        created_by=user.user_id,
    )
    db.add(upload)
    db.commit()

    return ApiResponse(data=InitUploadResponse(upload_id=upload.upload_id, doc_id=doc.doc_id))


# ── PUT /uploads/{upload_id}/parts/{part_no} ─────────────
@router.put("/uploads/{upload_id}/parts/{part_no}")
async def upload_part(
    upload_id: str,
    part_no: int,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """T4 – Upload a single chunk (idempotent by upload_id + part_no)."""
    upload = db.query(Upload).filter_by(upload_id=upload_id, tenant_id=user.tenant_id).first()
    if not upload:
        raise HTTPException(404, "Upload session not found")

    # Idempotency: check if part already exists
    existing = db.query(UploadPart).filter_by(upload_id=upload_id, part_no=part_no).first()
    if existing:
        return ApiResponse(data={"upload_id": upload_id, "part_no": part_no, "status": "already_uploaded"})

    body = await request.body()
    storage = LocalFSAdapter()
    rel = StoragePaths.upload_part(upload_id, part_no)
    storage.write(rel, body)

    part = UploadPart(
        upload_id=upload_id,
        part_no=part_no,
        size=len(body),
    )
    db.add(part)
    upload.status = "uploading"
    db.commit()

    return ApiResponse(data={"upload_id": upload_id, "part_no": part_no, "status": "uploaded"})


# ── POST /uploads/{upload_id}/complete ───────────────────
@router.post("/uploads/{upload_id}/complete", response_model=ApiResponse[CompleteUploadResponse])
def complete_upload(
    upload_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """T4 – Merge all chunks into the final PDF."""
    upload = db.query(Upload).filter_by(upload_id=upload_id, tenant_id=user.tenant_id).first()
    if not upload:
        raise HTTPException(404, "Upload session not found")

    storage = LocalFSAdapter()
    parts = db.query(UploadPart).filter_by(upload_id=upload_id).order_by(UploadPart.part_no).all()
    if not parts:
        raise HTTPException(400, "No parts uploaded")

    # Merge parts
    merged = bytearray()
    for part in parts:
        rel = StoragePaths.upload_part(upload_id, part.part_no)
        merged.extend(storage.read(rel))

    # Write final PDF
    doc_id = upload.doc_id
    rel_pdf = StoragePaths.original_pdf(doc_id)
    storage.write(rel_pdf, bytes(merged))

    # Update records
    upload.status = "completed"
    doc = db.query(Document).filter_by(doc_id=doc_id).first()
    if doc:
        doc.file_size = len(merged)
        doc.status = "uploaded"

    # Create initial version
    version = DocumentVersion(
        version_id=generate_ulid("ver"),
        doc_id=doc_id,
        tenant_id=user.tenant_id,
        version_no=1,
    )
    db.add(version)
    db.commit()

    return ApiResponse(
        data=CompleteUploadResponse(
            upload_id=upload_id,
            doc_id=doc_id,
            status="completed",
        )
    )


# ── GET /documents/{doc_id} ─────────────────────────────
@router.get("/documents/{doc_id}", response_model=ApiResponse[DocumentOut])
def get_document(
    doc_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter_by(doc_id=doc_id, tenant_id=user.tenant_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return ApiResponse(data=DocumentOut.model_validate(doc))


# ── GET /documents/{doc_id}/versions ─────────────────────
@router.get("/documents/{doc_id}/versions")
def list_versions(
    doc_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    versions = (
        db.query(DocumentVersion)
        .filter_by(doc_id=doc_id, tenant_id=user.tenant_id)
        .order_by(DocumentVersion.version_no)
        .all()
    )
    return ApiResponse(data=[DocumentVersionOut.model_validate(v) for v in versions])


# ── GET /documents/{doc_id}/versions/{ver_id}/pages/{page_no} ──
@router.get("/documents/{doc_id}/versions/{ver_id}/pages/{page_no}")
def get_page_image(
    doc_id: str,
    ver_id: str,
    page_no: int,
    user: CurrentUser = Depends(get_current_user),
):
    storage = LocalFSAdapter()
    rel = StoragePaths.page_image(doc_id, ver_id, page_no)
    if not storage.exists(rel):
        raise HTTPException(404, "Page image not found")
    return FileResponse(storage.abs_path(rel), media_type="image/png")
