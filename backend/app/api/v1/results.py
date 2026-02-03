"""T11 – Result aggregation API.

GET /api/v1/documents/{doc_id}/versions/{ver_id}/result  – Dashboard data
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.models import (
    DocumentVersion,
    EvidenceRef,
    LlmResult,
    Metric,
    MetricValue,
    Page,
    Risk,
)
from app.schemas.common import ApiResponse
from app.schemas.result import DashboardResult, EvidenceRefOut, MetricValueOut, RiskOut

router = APIRouter(tags=["results"])


@router.get("/documents/{doc_id}/versions/{ver_id}/result", response_model=ApiResponse[DashboardResult])
def get_dashboard_result(
    doc_id: str,
    ver_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate all parsed data for the Dashboard page."""
    version = (
        db.query(DocumentVersion)
        .filter_by(version_id=ver_id, doc_id=doc_id, tenant_id=user.tenant_id)
        .first()
    )
    if not version:
        raise HTTPException(404, "Version not found")

    # Page count
    page_count = db.query(Page).filter_by(version_id=ver_id).count()

    # Summary from LLM result
    llm_result = db.query(LlmResult).filter_by(version_id=ver_id).first()
    summary = llm_result.summary if llm_result else None

    # Metrics
    mv_rows = db.query(MetricValue).filter_by(version_id=ver_id).all()
    metrics_out: list[MetricValueOut] = []
    for mv in mv_rows:
        metric = db.query(Metric).filter_by(metric_id=mv.metric_id).first()
        refs = (
            db.query(EvidenceRef)
            .filter_by(source_type="metric_value", source_id=mv.mv_id)
            .all()
        )
        metrics_out.append(
            MetricValueOut(
                mv_id=mv.mv_id,
                metric_code=metric.code if metric else "",
                metric_name_cn=metric.name_cn if metric else "",
                unit=metric.unit if metric else None,
                period=mv.period,
                value=mv.value,
                value_text=mv.value_text,
                yoy_change=mv.yoy_change,
                needs_review=mv.needs_review,
                evidence_refs=[
                    EvidenceRefOut(
                        ref_id=r.ref_id,
                        page_no=r.page_no,
                        bbox_norm=r.bbox_norm,
                        snippet=r.snippet,
                    )
                    for r in refs
                ],
            )
        )

    # Risks
    risk_rows = db.query(Risk).filter_by(version_id=ver_id).all()
    risks_out: list[RiskOut] = []
    for r in risk_rows:
        refs = (
            db.query(EvidenceRef)
            .filter_by(source_type="risk", source_id=r.risk_id)
            .all()
        )
        risks_out.append(
            RiskOut(
                risk_id=r.risk_id,
                level=r.level,
                title=r.title,
                description=r.description,
                recommendation=r.recommendation,
                needs_review=r.needs_review,
                evidence_refs=[
                    EvidenceRefOut(
                        ref_id=ref.ref_id,
                        page_no=ref.page_no,
                        bbox_norm=ref.bbox_norm,
                        snippet=ref.snippet,
                    )
                    for ref in refs
                ],
            )
        )

    return ApiResponse(
        data=DashboardResult(
            version_id=ver_id,
            doc_id=doc_id,
            summary=summary,
            metrics=metrics_out,
            risks=risks_out,
            page_count=page_count,
        )
    )
