"""Operational alerts (Phase G).

Checked by the worker's background loop every REAPER_INTERVAL_SECONDS:
- failed-job spike: ALERT_FAILED_JOBS or more failures in ALERT_WINDOW_MINUTES
- queue backlog: more than ALERT_QUEUE_BACKLOG jobs waiting
- spend: today's estimated LLM spend at ALERT_SPEND_FRACTION of the daily ceiling

Each alert is a CRITICAL log line starting with "ALERT" (log platforms can page
on it) and, if ALERT_WEBHOOK_URL is set, a POST of {"text": ...} (Slack
incoming-webhook format). The same alert is sent at most once per
ALERT_COOLDOWN_SECONDS, so a long incident doesn't flood the channel.
"""
import logging
from datetime import timedelta

import httpx
from sqlalchemy import func

from src.config import limits, ops_settings
from src.database import SessionLocal
from src.models.jobs import Job, JobStatus

logger = logging.getLogger("grovii.alerts")

_DEDUP_PREFIX = "grovii:alert:"


def queue_length() -> int:
    from src.services.queue_service import storyboard_queue

    return int(storyboard_queue.count)


def spend_fraction() -> float:
    from src.services.spend_service import committed_spend_today

    ceiling = float(limits.DAILY_SPEND_LIMIT_USD or 0)
    if ceiling <= 0:
        return 0.0
    db = SessionLocal()
    try:
        return float(committed_spend_today(db)) / ceiling
    finally:
        db.close()


def failed_jobs_recent() -> int:
    db = SessionLocal()
    try:
        cutoff = func.now() - timedelta(minutes=ops_settings.ALERT_WINDOW_MINUTES)
        return int(db.query(func.count(Job.id)).filter(
            Job.status == JobStatus.FAILED,
            func.coalesce(Job.completed_at, Job.created_at) >= cutoff,
        ).scalar() or 0)
    finally:
        db.close()


def _post_webhook(text: str) -> None:
    url = ops_settings.ALERT_WEBHOOK_URL
    if not url:
        return
    try:
        httpx.post(url, json={"text": text}, timeout=5)
    except Exception as e:  # noqa: BLE001 - alerting must never crash the worker
        logger.error("Alert webhook failed: %s", type(e).__name__)


def _first_time(name: str) -> bool:
    """True if this alert wasn't sent within the cooldown (Redis SET NX)."""
    try:
        from src.services.redis_service import redis_client

        return bool(redis_client.set(_DEDUP_PREFIX + name, "1", nx=True, ex=ops_settings.ALERT_COOLDOWN_SECONDS))
    except Exception:  # noqa: BLE001 - Redis down: alert anyway
        return True


def check_and_alert() -> list[str]:
    """Run every check; return the names of alerts sent now."""
    found: dict[str, str] = {}
    try:
        failed = failed_jobs_recent()
        if failed >= ops_settings.ALERT_FAILED_JOBS:
            found["failed_jobs"] = (f"{failed} generations failed in the last {ops_settings.ALERT_WINDOW_MINUTES} min "
                                    "(AI provider down? check /health/deep and the RUNBOOK).")
    except Exception as e:  # noqa: BLE001
        logger.error("Alert check failed_jobs errored: %s", type(e).__name__)
    try:
        waiting = queue_length()
        if waiting > ops_settings.ALERT_QUEUE_BACKLOG:
            found["queue_backlog"] = f"{waiting} generations waiting in the queue (workers down or too few?)."
    except Exception as e:  # noqa: BLE001
        logger.error("Alert check queue_backlog errored: %s", type(e).__name__)
    try:
        frac = spend_fraction()
        if frac >= ops_settings.ALERT_SPEND_FRACTION:
            found["spend"] = f"LLM spend today is at {frac:.0%} of the daily ceiling (${limits.DAILY_SPEND_LIMIT_USD})."
    except Exception as e:  # noqa: BLE001
        logger.error("Alert check spend errored: %s", type(e).__name__)

    sent = []
    for name, text in found.items():
        if not _first_time(name):
            continue
        logger.critical("ALERT %s: %s", name, text, extra={"event": "alert", "alert": name})
        _post_webhook(f"[Grovii] {text}")
        sent.append(name)
    return sent
