"""T2 – SQLAlchemy ORM models for all 18+ tables.

Naming conventions
──────────────────
PK format:  CHAR(26)  with ULID prefix  (e.g. ``doc_01J…``, ``job_01J…``)
Timestamps: TIMESTAMP(3) UTC
Charset:    utf8mb4 / InnoDB
Bbox:       JSON array [x0, y0, x1, y1] normalised to [0, 1]

Every business table carries ``tenant_id`` with a composite index
``(tenant_id, created_at)`` for multi-tenant isolation.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.ulid import generate_ulid

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CHAR26 = String(30)  # CHAR(26) + small margin for prefix


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════
# 1. tenants
# ═══════════════════════════════════════════════════════════════════════════
class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("tnt"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ═══════════════════════════════════════════════════════════════════════════
# 2. users  (RBAC)
# ═══════════════════════════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("usr"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="analyst")  # admin / analyst / viewer
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_users_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3. documents  (logical parent)
# ═══════════════════════════════════════════════════════════════════════════
class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("doc"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    created_by: Mapped[Optional[str]] = mapped_column(CHAR26, ForeignKey("users.user_id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions = relationship("DocumentVersion", back_populates="document", lazy="selectin")

    __table_args__ = (
        Index("ix_documents_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 4. uploads  (chunk upload session)
# ═══════════════════════════════════════════════════════════════════════════
class Upload(Base):
    __tablename__ = "uploads"

    upload_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("upl"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    doc_id: Mapped[Optional[str]] = mapped_column(CHAR26, ForeignKey("documents.doc_id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    total_parts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="initiated")  # initiated / uploading / completed / failed
    created_by: Mapped[Optional[str]] = mapped_column(CHAR26, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parts = relationship("UploadPart", back_populates="upload", lazy="selectin")

    __table_args__ = (
        Index("ix_uploads_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 5. upload_parts  (idempotent part tracking)
# ═══════════════════════════════════════════════════════════════════════════
class UploadPart(Base):
    __tablename__ = "upload_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("uploads.upload_id"), nullable=False)
    part_no: Mapped[int] = mapped_column(Integer, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0)
    md5: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    upload = relationship("Upload", back_populates="parts")

    __table_args__ = (
        Index("uq_upload_part", "upload_id", "part_no", unique=True),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 6. document_versions  (immutable parse snapshot)
# ═══════════════════════════════════════════════════════════════════════════
class DocumentVersion(Base):
    __tablename__ = "document_versions"

    version_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("ver"))
    doc_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("documents.doc_id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    parse_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="versions")

    __table_args__ = (
        Index("ix_docver_tenant_created", "tenant_id", "created_at"),
        Index("ix_docver_doc", "doc_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 7. jobs  (task state machine)
# ═══════════════════════════════════════════════════════════════════════════
class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("job"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    version_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("document_versions.version_id"), nullable=False)
    doc_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("documents.doc_id"), nullable=False)
    stage: Mapped[str] = mapped_column(
        String(30), default="queued"
    )  # queued / preprocess / ocr / extract / llm / index / done / failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_jobs_tenant_created", "tenant_id", "created_at"),
        Index("ix_jobs_version", "version_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 8. pages  (page metadata)
# ═══════════════════════════════════════════════════════════════════════════
class Page(Base):
    __tablename__ = "pages"

    page_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("pag"))
    version_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("document_versions.version_id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumb_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ocr_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_pages_tenant_created", "tenant_id", "created_at"),
        Index("uq_page_version_no", "version_id", "page_no", unique=True),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 9. ocr_blocks  (bbox normalised to [0,1])
# ═══════════════════════════════════════════════════════════════════════════
class OcrBlock(Base):
    __tablename__ = "ocr_blocks"

    block_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("blk"))
    page_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("pages.page_id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    block_type: Mapped[str] = mapped_column(String(30), default="text")  # text / table / figure
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bbox: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [x0, y0, x1, y1] normalised
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_ocrblocks_page", "page_id"),
        Index("ix_ocrblocks_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 10. evidence_refs  (page + bbox references)
# ═══════════════════════════════════════════════════════════════════════════
class EvidenceRef(Base):
    __tablename__ = "evidence_refs"

    ref_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("evr"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)  # metric_value / risk / chat_message
    source_id: Mapped[str] = mapped_column(CHAR26, nullable=False)
    page_id: Mapped[Optional[str]] = mapped_column(CHAR26, ForeignKey("pages.page_id"), nullable=True)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_norm: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [x0, y0, x1, y1] ∈ [0,1]
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_evidrefs_source", "source_type", "source_id"),
        Index("ix_evidrefs_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 11. metrics  (KPI dictionary)
# ═══════════════════════════════════════════════════════════════════════════
class Metric(Base):
    __tablename__ = "metrics"

    metric_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("met"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. revenue, net_profit
    name_cn: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 万元, %, 次
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("uq_metric_tenant_code", "tenant_id", "code", unique=True),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 12. metric_values  (by version + period)
# ═══════════════════════════════════════════════════════════════════════════
class MetricValue(Base):
    __tablename__ = "metric_values"

    mv_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("mvl"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    version_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("document_versions.version_id"), nullable=False)
    metric_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("metrics.metric_id"), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2023", "2023-H1"
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    yoy_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_metval_version", "version_id"),
        Index("ix_metval_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 13. risks  (high / medium / low)
# ═══════════════════════════════════════════════════════════════════════════
class Risk(Base):
    __tablename__ = "risks"

    risk_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("rsk"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    version_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("document_versions.version_id"), nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)  # high / medium / low
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_risks_version", "version_id"),
        Index("ix_risks_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 14. export_tasks
# ═══════════════════════════════════════════════════════════════════════════
class ExportTask(Base):
    __tablename__ = "export_tasks"

    export_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("exp"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    version_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("document_versions.version_id"), nullable=False)
    format: Mapped[str] = mapped_column(String(10), default="docx")  # docx / pdf
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / processing / done / failed
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(CHAR26, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_exports_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 15. chat_sessions  (Q&A)
# ═══════════════════════════════════════════════════════════════════════════
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("css"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    version_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("document_versions.version_id"), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(CHAR26, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship("ChatMessage", back_populates="session", lazy="selectin")

    __table_args__ = (
        Index("ix_chatsess_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 16. chat_messages
# ═══════════════════════════════════════════════════════════════════════════
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("msg"))
    session_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("chat_sessions.session_id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_chatmsg_session", "session_id"),
        Index("ix_chatmsg_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 17. embedding_chunks  (vector index – optional V1)
# ═══════════════════════════════════════════════════════════════════════════
class EmbeddingChunk(Base):
    __tablename__ = "embedding_chunks"

    chunk_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("chk"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    version_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("document_versions.version_id"), nullable=False)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Qdrant point id
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_embchunk_version", "version_id"),
        Index("ix_embchunk_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 18. audit_logs
# ═══════════════════════════════════════════════════════════════════════════
class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("aud"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(CHAR26, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(CHAR26, nullable=True)
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_auditlog_tenant_created", "tenant_id", "created_at"),
        Index("ix_auditlog_resource", "resource_type", "resource_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 19. llm_results  (LLM output cache)
# ═══════════════════════════════════════════════════════════════════════════
class LlmResult(Base):
    __tablename__ = "llm_results"

    result_id: Mapped[str] = mapped_column(CHAR26, primary_key=True, default=lambda: generate_ulid("llm"))
    tenant_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("tenants.tenant_id"), nullable=False)
    version_id: Mapped[str] = mapped_column(CHAR26, ForeignKey("document_versions.version_id"), nullable=False)
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kpis_overrides: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    risks_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_llmresult_version", "version_id"),
        Index("ix_llmresult_tenant_created", "tenant_id", "created_at"),
    )
