import time
import logging
import requests

from database import SessionLocal
from models import MonitoredURL, HealthCheck

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitor")

REQUEST_TIMEOUT_SECONDS = 10


def ping_url(url: str):
    """Hit a single URL and return (status_code, response_time_ms, is_up, error_message)."""
    start = time.perf_counter()
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        is_up = 200 <= resp.status_code < 400
        return resp.status_code, elapsed_ms, is_up, None
    except requests.exceptions.RequestException as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return None, elapsed_ms, False, str(exc)


def check_all_urls():
    """Runs on the scheduler thread every minute. Opens its own DB session
    because the FastAPI request-scoped session can't be shared across threads."""
    db = SessionLocal()
    try:
        urls = db.query(MonitoredURL).all()
        for entry in urls:
            status_code, response_time_ms, is_up, error_message = ping_url(entry.url)
            check = HealthCheck(
                url_id=entry.id,
                status_code=status_code,
                response_time_ms=response_time_ms,
                is_up=is_up,
                error_message=error_message,
            )
            db.add(check)
            logger.info(
                "Checked %s -> up=%s status=%s (%sms)",
                entry.url,
                is_up,
                status_code,
                response_time_ms,
            )
        db.commit()
    finally:
        db.close()
