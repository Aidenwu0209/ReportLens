"""T9 – Metric extraction + evidence mapping.

Extracts structured financial metrics from OCR blocks and maps
evidence references (page + bbox) for each value.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import (
    EvidenceRef,
    Job,
    Metric,
    MetricValue,
    OcrBlock,
    Page,
)
from app.services.storage import LocalFSAdapter, StoragePaths
from app.utils.ulid import generate_ulid

logger = logging.getLogger(__name__)

# ── Known metric patterns (regex) ──────────────────────
METRIC_PATTERNS: list[dict[str, Any]] = [
    {"code": "revenue", "name_cn": "营业收入", "unit": "万元", "patterns": [r"营业收入[：:\s]*([\d,\.]+)"]},
    {"code": "net_profit", "name_cn": "净利润", "unit": "万元", "patterns": [r"净利润[：:\s]*([\d,\.]+)"]},
    {"code": "total_assets", "name_cn": "总资产", "unit": "万元", "patterns": [r"总资产[：:\s]*([\d,\.]+)"]},
    {"code": "total_liabilities", "name_cn": "总负债", "unit": "万元", "patterns": [r"总负债[：:\s]*([\d,\.]+)"]},
    {"code": "equity", "name_cn": "股东权益", "unit": "万元", "patterns": [r"(?:股东权益|所有者权益)[：:\s]*([\d,\.]+)"]},
    {"code": "eps", "name_cn": "每股收益", "unit": "元", "patterns": [r"每股收益[：:\s]*([\d,\.]+)"]},
    {"code": "roe", "name_cn": "净资产收益率", "unit": "%", "patterns": [r"净资产收益率[：:\s]*([\d,\.]+)"]},
    {"code": "gross_margin", "name_cn": "毛利率", "unit": "%", "patterns": [r"毛利率[：:\s]*([\d,\.]+)"]},
    {"code": "debt_ratio", "name_cn": "资产负债率", "unit": "%", "patterns": [r"资产负债率[：:\s]*([\d,\.]+)"]},
    {"code": "operating_cash_flow", "name_cn": "经营性现金流", "unit": "万元", "patterns": [r"经营(?:活动产生的|性)现金流[量净额]*[：:\s]*([\d,\.]+)"]},
]


def _parse_number(text: str) -> float | None:
    """Try to parse a Chinese-formatted number."""
    cleaned = text.replace(",", "").replace("，", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


@celery_app.task(name="app.tasks.extract.extract_metrics", bind=True, max_retries=2)
def extract_metrics(self, job_id: str, doc_id: str, version_id: str) -> dict:
    """Extract financial metrics from OCR blocks, create metric_values + evidence_refs."""
    db = SessionLocal()
    storage = LocalFSAdapter()

    try:
        job = db.query(Job).filter_by(job_id=job_id).first()
        if job:
            job.stage = "extract"
            job.progress = 60
            db.commit()

        tenant_id = job.tenant_id if job else ""

        # Gather all OCR text blocks for this version
        pages = db.query(Page).filter_by(version_id=version_id).order_by(Page.page_no).all()
        page_map = {p.page_id: p for p in pages}

        blocks = (
            db.query(OcrBlock)
            .filter(OcrBlock.page_id.in_([p.page_id for p in pages]))
            .order_by(OcrBlock.seq)
            .all()
        )

        extracted: list[dict] = []

        for mp in METRIC_PATTERNS:
            # Ensure metric dictionary entry exists
            metric = db.query(Metric).filter_by(tenant_id=tenant_id, code=mp["code"]).first()
            if not metric:
                metric = Metric(
                    metric_id=generate_ulid("met"),
                    tenant_id=tenant_id,
                    code=mp["code"],
                    name_cn=mp["name_cn"],
                    unit=mp.get("unit"),
                )
                db.add(metric)
                db.flush()

            for block in blocks:
                if not block.text:
                    continue
                for pattern in mp["patterns"]:
                    m = re.search(pattern, block.text)
                    if m:
                        value = _parse_number(m.group(1))
                        page = page_map.get(block.page_id)

                        # Create metric value
                        mv = MetricValue(
                            mv_id=generate_ulid("mvl"),
                            tenant_id=tenant_id,
                            version_id=version_id,
                            metric_id=metric.metric_id,
                            period="latest",
                            value=value,
                            value_text=m.group(1),
                            needs_review=(value is None),
                        )
                        db.add(mv)
                        db.flush()

                        # Create evidence ref
                        ev = EvidenceRef(
                            ref_id=generate_ulid("evr"),
                            tenant_id=tenant_id,
                            source_type="metric_value",
                            source_id=mv.mv_id,
                            page_id=block.page_id,
                            page_no=page.page_no if page else 0,
                            bbox_norm=block.bbox,
                            snippet=block.text[:200],
                        )
                        db.add(ev)

                        extracted.append({
                            "code": mp["code"],
                            "value": value,
                            "page_no": page.page_no if page else 0,
                        })
                        break  # one match per metric per block scan
                else:
                    continue
                break  # found match for this metric pattern

        db.commit()

        # Save artifacts
        metrics_artifact = json.dumps(extracted, ensure_ascii=False)
        rel = StoragePaths.artifact(doc_id, version_id, "metrics.json")
        storage.write(rel, metrics_artifact.encode())

        if job:
            job.progress = 70
            db.commit()

        logger.info("Extracted %d metrics for version %s", len(extracted), version_id)
        return {"doc_id": doc_id, "version_id": version_id, "metrics_count": len(extracted)}

    except Exception as exc:
        db.rollback()
        logger.exception("Extraction failed for job %s", job_id)
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()
