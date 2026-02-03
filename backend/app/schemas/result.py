"""Dashboard / result aggregation schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class EvidenceRefOut(BaseModel):
    ref_id: str
    page_no: int
    bbox_norm: Optional[list] = None
    snippet: Optional[str] = None


class MetricValueOut(BaseModel):
    mv_id: str
    metric_code: str
    metric_name_cn: str
    unit: Optional[str] = None
    period: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    yoy_change: Optional[float] = None
    needs_review: bool = False
    evidence_refs: list[EvidenceRefOut] = []


class RiskOut(BaseModel):
    risk_id: str
    level: str
    title: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    needs_review: bool = False
    evidence_refs: list[EvidenceRefOut] = []


class DashboardResult(BaseModel):
    version_id: str
    doc_id: str
    summary: Optional[str] = None
    metrics: list[MetricValueOut] = []
    risks: list[RiskOut] = []
    page_count: int = 0
