"""Stuck-job reaper.

Marks jobs that are stuck as failed, and refunds them:
- queued longer than QUEUED_TIMEOUT_MINUTES (no worker picked them up), or
- running longer than RUNNING_TIMEOUT_MINUTES (the worker died mid-job, or
  every attempt plus retries should have finished by now).

Safe to run from several processes at once: rows are locked with SKIP LOCKED,
the status change is a no-op the second time, and refunds happen at most once.

Runs every REAPER_INTERVAL_SECONDS inside each worker process (see worker.py),
or once from cron:  python -m src.services.reaper
"""
import logging
import threading
from datetime import timedelta

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from src.config import jobs as job_config
from src.database import SessionLocal
from src.models.jobs import Job, JobStatus
from src.services.job_lifecycle import USER_MESSAGES, transition

logger = logging.getLogger("grovii.reaper")


def reap_stuck_jobs(db: Session) -> int:
    # Compare in SQL against the database clock, so app-server clock skew and
    # naive/aware timestamp columns cannot cause false positives.
    queued_cutoff = func.now() - timedelta(minutes=job_config.QUEUED_TIMEOUT_MINUTES)
    running_cutoff = func.now() - timedelta(minutes=job_config.RUNNING_TIMEOUT_MINUTES)
    stuck_ids = [
        row.id for row in db.query(Job.id).filter(or_(
            and_(Job.status == JobStatus.QUEUED, Job.created_at < queued_cutoff),
            and_(Job.status == JobStatus.RUNNING,
                 func.coalesce(Job.started_at, Job.created_at) < running_cutoff),
        )).with_for_update(skip_locked=True).all()
    ]
    for job_id in stuck_ids:
        logger.warning("Reaping stuck job %s", job_id)
        transition(db, job_id, JobStatus.FAILED, reason=USER_MESSAGES["timeout"],
                   internal_error="reaped: stuck past timeout", refund=True)
    db.commit()  # release locks if nothing was stuck
    return len(stuck_ids)


def run_once() -> int:
    db = SessionLocal()
    try:
        return reap_stuck_jobs(db)
    finally:
        db.close()


def start_background_reaper(stop: threading.Event | None = None) -> threading.Thread:
    stop = stop or threading.Event()

    def loop():
        while not stop.wait(job_config.REAPER_INTERVAL_SECONDS):
            try:
                count = run_once()
                if count:
                    logger.warning("Reaper failed and refunded %s stuck job(s)", count)
            except Exception as e:  # noqa: BLE001 - keep the loop alive
                logger.error("Reaper run failed: %s", type(e).__name__)
            try:
                from src.services.ops_alerts import check_and_alert

                check_and_alert()  # failed-job spikes, queue backlog, spend (Phase G)
            except Exception as e:  # noqa: BLE001
                logger.error("Alert check failed: %s", type(e).__name__)

    thread = threading.Thread(target=loop, name="grovii-reaper", daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Reaped {run_once()} stuck job(s)")
