"""T10 – LLM insight generation task (Wenxin 5.0).

Calls the Wenxin adapter, validates output, persists summary + risks,
and creates evidence_refs for each risk.
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.adapters.wenxin_llm import (
    LlmInsightOutput,
    compute_input_hash,
    generate_insights,
)
from app.models.models import (
    EvidenceRef,
    Job,
    LlmResult,
    MetricValue,
    OcrBlock,
    Page,
    Risk,
)
from app.services.storage import LocalFSAdapter, StoragePaths
from app.utils.ulid import generate_ulid

logger = logging.getLogger(__name__)


def _gather_chunks(db, version_id: str, max_chars: int = 8000) -> str:
    """Concatenate OCR text up to *max_chars* for LLM context."""
    pages = db.query(Page).filter_by(version_id=version_id).order_by(Page.page_no).all()
    blocks = (
        db.query(OcrBlock)
        .filter(OcrBlock.page_id.in_([p.page_id for p in pages]))
        .order_by(OcrBlock.seq)
        .all()
    )
    chunks: list[str] = []
    total = 0
    for b in blocks:
        if b.text and total < max_chars:
            chunks.append(b.text)
            total += len(b.text)
    return "\n".join(chunks)


@celery_app.task(name="app.tasks.llm.llm_generate_insights", bind=True, max_retries=1)
def llm_generate_insights(self, job_id: str, doc_id: str, version_id: str) -> dict:
    """Generate LLM insights and persist results."""
    db = SessionLocal()
    storage = LocalFSAdapter()

    try:
        job = db.query(Job).filter_by(job_id=job_id).first()
        if job:
            job.stage = "llm"
            job.progress = 75
            db.commit()

        tenant_id = job.tenant_id if job else ""

        # Build input
        metrics_data = (
            db.query(MetricValue).filter_by(version_id=version_id).all()
        )
        metrics_json = json.dumps(
            [{"mv_id": m.mv_id, "value": m.value, "period": m.period} for m in metrics_data],
            ensure_ascii=False,
        )
        chunks_text = _gather_chunks(db, version_id)

        # Check cache by input hash
        input_hash = compute_input_hash(metrics_json, chunks_text, "v1")
        existing = db.query(LlmResult).filter_by(input_hash=input_hash).first()
        if existing:
            logger.info("LLM cache hit for hash %s", input_hash)
            if job:
                job.stage = "done"
                job.progress = 100
                db.commit()
            return {"cached": True, "result_id": existing.result_id}

        # Call LLM
        loop = asyncio.new_event_loop()
        output: LlmInsightOutput = loop.run_until_complete(
            generate_insights(metrics_json, chunks_text)
        )
        loop.close()

        # Persist LLM result
        llm_result = LlmResult(
            result_id=generate_ulid("llm"),
            tenant_id=tenant_id,
            version_id=version_id,
            input_hash=input_hash,
            prompt_version="v1",
            summary=output.summary,
            kpis_overrides=([k.model_dump() for k in output.kpis_overrides] if output.kpis_overrides else None),
            risks_json=([r.model_dump() for r in output.risks] if output.risks else None),
            recommendations=output.recommendations or None,
            raw_response=output.model_dump(),
        )
        db.add(llm_result)

        # Persist risks with evidence
        for r in output.risks:
            risk = Risk(
                risk_id=generate_ulid("rsk"),
                tenant_id=tenant_id,
                version_id=version_id,
                level=r.level,
                title=r.title,
                description=r.description,
                recommendation=r.recommendation,
                needs_review=(len(r.evidence_refs) == 0),
            )
            db.add(risk)
            db.flush()

            for ev in r.evidence_refs:
                evidence = EvidenceRef(
                    ref_id=generate_ulid("evr"),
                    tenant_id=tenant_id,
                    source_type="risk",
                    source_id=risk.risk_id,
                    page_no=ev.page_no,
                    bbox_norm=ev.bbox_norm,
                    snippet=ev.snippet,
                )
                db.add(evidence)

        db.commit()

        # Save artifact
        rel = StoragePaths.artifact(doc_id, version_id, "llm_output.json")
        storage.write(rel, json.dumps(output.model_dump(), ensure_ascii=False).encode())

        if job:
            job.stage = "done"
            job.progress = 100
            db.commit()

        logger.info("LLM insights generated for version %s", version_id)
        return {"version_id": version_id, "result_id": llm_result.result_id}

    except Exception as exc:
        db.rollback()
        logger.exception("LLM task failed for job %s", job_id)
        if job:
            job.stage = "failed"
            job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
