"""T5 – Job orchestration: the main pipeline that chains all tasks.

Pipeline:
  run_job(version_id)
    → preprocess_pdf  (q_preprocess)
      → ocr_all_pages (q_ocr)
        → extract_metrics (q_extract)
          → llm_generate_insights (q_llm)
            → done
"""

from __future__ import annotations

import datetime as dt
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import Job

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.pipeline.run_job", bind=True, max_retries=0)
def run_job(self, job_id: str, doc_id: str, version_id: str) -> dict:
    """Master orchestrator – runs the full parse pipeline sequentially.

    Each sub-task updates the job stage/progress.  On failure the job is
    marked *failed* and the error message is stored for DLQ replay.
    """
    db = SessionLocal()

    try:
        job = db.query(Job).filter_by(job_id=job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.started_at = dt.datetime.now(dt.timezone.utc)
        job.stage = "queued"
        job.progress = 0
        db.commit()

        # 1. Preprocess
        from app.tasks.preprocess import preprocess_pdf
        preprocess_pdf(job_id=job_id, doc_id=doc_id, version_id=version_id)

        # 2. OCR
        from app.tasks.ocr import ocr_all_pages
        ocr_all_pages(job_id=job_id, doc_id=doc_id, version_id=version_id)

        # 3. Extract
        from app.tasks.extract import extract_metrics
        extract_metrics(job_id=job_id, doc_id=doc_id, version_id=version_id)

        # 4. LLM
        from app.tasks.llm import llm_generate_insights
        llm_generate_insights(job_id=job_id, doc_id=doc_id, version_id=version_id)

        # Done
        job = db.query(Job).filter_by(job_id=job_id).first()
        if job:
            job.stage = "done"
            job.progress = 100
            job.finished_at = dt.datetime.now(dt.timezone.utc)
            db.commit()

        logger.info("Pipeline completed for job %s", job_id)
        return {"job_id": job_id, "status": "done"}

    except Exception as exc:
        db.rollback()
        job = db.query(Job).filter_by(job_id=job_id).first()
        if job:
            job.stage = "failed"
            job.error_message = str(exc)
            job.finished_at = dt.datetime.now(dt.timezone.utc)
            db.commit()
        logger.exception("Pipeline failed for job %s", job_id)
        return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
