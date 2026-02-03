"""Celery application factory.

Queues follow the specification:
  q_preprocess  – pdf_to_images, deskew          (concurrency 2-4)
  q_ocr         – ocr_page                       (concurrency 3-8)
  q_extract     – extract_tables_metrics          (concurrency 2-4)
  q_llm         – llm_summary_risks              (concurrency 1-3)
  q_index       – build_vector_index (optional)   (concurrency 1-2)
  q_export      – render_docx_pdf                (concurrency 1-2)
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "annual_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "app.tasks.preprocess.*": {"queue": "q_preprocess"},
        "app.tasks.ocr.*": {"queue": "q_ocr"},
        "app.tasks.extract.*": {"queue": "q_extract"},
        "app.tasks.llm.*": {"queue": "q_llm"},
        "app.tasks.index.*": {"queue": "q_index"},
        "app.tasks.export.*": {"queue": "q_export"},
    },
    task_queues={
        "q_preprocess": {"exchange": "q_preprocess", "routing_key": "q_preprocess"},
        "q_ocr": {"exchange": "q_ocr", "routing_key": "q_ocr"},
        "q_extract": {"exchange": "q_extract", "routing_key": "q_extract"},
        "q_llm": {"exchange": "q_llm", "routing_key": "q_llm"},
        "q_index": {"exchange": "q_index", "routing_key": "q_index"},
        "q_export": {"exchange": "q_export", "routing_key": "q_export"},
    },
    task_default_queue="q_preprocess",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"])
