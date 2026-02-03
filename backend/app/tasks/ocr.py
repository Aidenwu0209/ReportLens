"""T8 – OCR tasks (PaddleOCR-VL 1.5 integration).

Runs OCR on each page image and stores normalised blocks.
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.adapters.paddle_ocr import ocr_page
from app.models.models import Job, OcrBlock, Page
from app.services.storage import LocalFSAdapter, StoragePaths
from app.utils.ulid import generate_ulid

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.ocr.ocr_single_page", bind=True, max_retries=3)
def ocr_single_page(self, job_id: str, page_id: str, image_path: str, width: int, height: int) -> dict:
    """Run OCR on a single page and persist blocks."""
    db = SessionLocal()
    storage = LocalFSAdapter()

    try:
        # Call async OCR adapter from sync celery task
        loop = asyncio.new_event_loop()
        blocks = loop.run_until_complete(ocr_page(storage.abs_path(image_path), width, height))
        loop.close()

        page_rec = db.query(Page).filter_by(page_id=page_id).first()
        tenant_id = page_rec.tenant_id if page_rec else ""

        for idx, block in enumerate(blocks):
            ocr_block = OcrBlock(
                block_id=generate_ulid("blk"),
                page_id=page_id,
                tenant_id=tenant_id,
                block_type=block.get("type", "text"),
                text=block.get("text", ""),
                bbox=block.get("bbox"),
                confidence=block.get("conf", 0.0),
                seq=idx,
            )
            db.add(ocr_block)

        if page_rec:
            page_rec.ocr_status = "done"

        db.commit()

        # Save OCR JSON to storage
        version_id = page_rec.version_id if page_rec else ""
        doc_id = ""
        job = db.query(Job).filter_by(job_id=job_id).first()
        if job:
            doc_id = job.doc_id

        if doc_id and version_id and page_rec:
            rel_json = StoragePaths.ocr_page_json(doc_id, version_id, page_rec.page_no)
            storage.write(rel_json, json.dumps(blocks, ensure_ascii=False).encode())

        return {"page_id": page_id, "block_count": len(blocks)}

    except Exception as exc:
        db.rollback()
        logger.exception("OCR failed for page %s", page_id)
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
    finally:
        db.close()


@celery_app.task(name="app.tasks.ocr.ocr_all_pages", bind=True, max_retries=1)
def ocr_all_pages(self, job_id: str, doc_id: str, version_id: str) -> dict:
    """Dispatch OCR for all pages of a version, then aggregate."""
    db = SessionLocal()

    try:
        job = db.query(Job).filter_by(job_id=job_id).first()
        if job:
            job.stage = "ocr"
            job.progress = 20
            db.commit()

        pages = db.query(Page).filter_by(version_id=version_id).order_by(Page.page_no).all()

        total = len(pages)
        for idx, page in enumerate(pages):
            try:
                ocr_single_page(
                    job_id=job_id,
                    page_id=page.page_id,
                    image_path=page.image_path,
                    width=page.width or 1,
                    height=page.height or 1,
                )
            except Exception as exc:
                logger.error("OCR failed for page %s: %s", page.page_id, exc)
                page.ocr_status = "failed"
                db.commit()

            if job:
                job.progress = 20 + int(40 * (idx + 1) / max(total, 1))
                db.commit()

        logger.info("OCR completed for %d pages, doc %s", total, doc_id)
        return {"doc_id": doc_id, "version_id": version_id, "pages_processed": total}

    except Exception as exc:
        db.rollback()
        logger.exception("OCR all pages failed for job %s", job_id)
        raise
    finally:
        db.close()
