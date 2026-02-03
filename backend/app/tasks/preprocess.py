"""T7 – PDF preprocessing tasks.

Pipeline: pdf → page images (PNG) + thumbnails (JPG).
Uses PyMuPDF (fitz) for PDF rendering.
"""

from __future__ import annotations

import logging
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import DocumentVersion, Job, Page
from app.services.storage import LocalFSAdapter, StoragePaths
from app.utils.ulid import generate_ulid

logger = logging.getLogger(__name__)

DPI = 200
THUMB_SIZE = (280, 400)


@celery_app.task(name="app.tasks.preprocess.preprocess_pdf", bind=True, max_retries=2)
def preprocess_pdf(self, job_id: str, doc_id: str, version_id: str) -> dict:
    """Convert each PDF page to PNG + thumbnail.

    Updates pages table and job progress.
    """
    storage = LocalFSAdapter()
    db = SessionLocal()

    try:
        # Update job stage
        job = db.query(Job).filter_by(job_id=job_id).first()
        if job:
            job.stage = "preprocess"
            job.progress = 5
            db.commit()

        # Open original PDF
        pdf_path = storage.abs_path(StoragePaths.original_pdf(doc_id))
        doc = fitz.open(pdf_path)
        page_count = len(doc)

        for i in range(page_count):
            page = doc[i]
            page_no = i + 1

            # Render page to PNG
            mat = fitz.Matrix(DPI / 72, DPI / 72)
            pix = page.get_pixmap(matrix=mat)
            png_bytes = pix.tobytes("png")
            width, height = pix.width, pix.height

            rel_img = StoragePaths.page_image(doc_id, version_id, page_no)
            storage.write(rel_img, png_bytes)

            # Generate thumbnail
            img = Image.open(BytesIO(png_bytes))
            img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
            thumb_buf = BytesIO()
            img.save(thumb_buf, format="JPEG", quality=85)
            rel_thumb = StoragePaths.page_thumb(doc_id, version_id, page_no)
            storage.write(rel_thumb, thumb_buf.getvalue())

            # Insert page record
            page_rec = Page(
                page_id=generate_ulid("pag"),
                version_id=version_id,
                tenant_id=job.tenant_id if job else "",
                page_no=page_no,
                width=width,
                height=height,
                image_path=rel_img,
                thumb_path=rel_thumb,
                ocr_status="pending",
            )
            db.add(page_rec)

            # Update progress
            if job:
                job.progress = 5 + int(15 * (i + 1) / page_count)
                db.commit()

        doc.close()
        db.commit()

        logger.info("Preprocessed %d pages for doc %s", page_count, doc_id)
        return {"page_count": page_count, "doc_id": doc_id, "version_id": version_id}

    except Exception as exc:
        db.rollback()
        logger.exception("Preprocess failed for job %s", job_id)
        if job:
            job.stage = "failed"
            job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()
