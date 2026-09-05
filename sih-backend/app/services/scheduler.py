"""
Optional background job that periodically re-runs the FIRMS ingestion +
classification pipeline, so the dashboard stays fresh without a human
hitting /fires/ingest manually.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.classifier import ingest_and_classify
from app.services.firms_client import FirmsClientError

logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()


def _run_ingestion_job():
    db = SessionLocal()
    try:
        result = ingest_and_classify(db)
        logger.info("Auto-ingestion complete: %s", result)
    except FirmsClientError as e:
        logger.warning("Auto-ingestion skipped: %s", e)
    finally:
        db.close()


def start_scheduler():
    if not settings.AUTO_INGEST_ENABLED:
        return
    scheduler.add_job(
        _run_ingestion_job,
        "interval",
        minutes=settings.AUTO_INGEST_INTERVAL_MINUTES,
        id="firms_ingestion",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
