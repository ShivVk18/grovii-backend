"""Recording per-job LLM spend and enforcing the global daily spend ceiling."""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.config import limits
from src.models.jobs import Job, JobStatus
from src.services.llm_usage import UsageMeter

logger = logging.getLogger("grovii.spend")


def record_job_usage(db: Session, job_id: str, meter: UsageMeter) -> None:
    db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            prompt_tokens=meter.prompt_tokens,
            completion_tokens=meter.completion_tokens,
            llm_calls=meter.calls,
            cost_usd=Decimal(str(round(meter.cost_usd, 6))),
        )
    )
    db.commit()
    logger.info(
        "Job %s LLM usage: %s calls, %s prompt + %s completion tokens, ~$%.4f",
        job_id, meter.calls, meter.prompt_tokens, meter.completion_tokens, meter.cost_usd,
    )


def _start_of_utc_day() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def committed_spend_today(db: Session) -> float:
    """Recorded spend of today's jobs, plus a worst-case reserve for every job
    created today that has not recorded its cost yet (queued or running)."""
    since = _start_of_utc_day()
    recorded = db.query(func.coalesce(func.sum(Job.cost_usd), 0)).filter(Job.created_at >= since).scalar()
    in_flight = (
        db.query(func.count(Job.id))
        .filter(
            Job.created_at >= since,
            Job.cost_usd.is_(None),
            Job.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),
        )
        .scalar()
    )
    return float(recorded) + in_flight * limits.JOB_COST_RESERVE_USD


_alerted_days: set[str] = set()


def ensure_daily_budget_available(db: Session) -> None:
    """Refuse a new job (503) if it could push today's spend over the ceiling."""
    committed = committed_spend_today(db)
    if committed + limits.JOB_COST_RESERVE_USD <= limits.DAILY_SPEND_LIMIT_USD:
        return
    day = _start_of_utc_day().date().isoformat()
    # Phase G wires CRITICAL logs to real alerting; until then this is a log line.
    logger.critical(
        "ALERT daily spend ceiling reached (%s): committed $%.2f of $%.2f limit; new generations refused%s",
        day, committed, limits.DAILY_SPEND_LIMIT_USD, "" if day not in _alerted_days else " (repeat)",
    )
    _alerted_days.add(day)
    raise AppError(
        503, "daily_limit_reached",
        "Grovii has reached today's generation limit. Please try again tomorrow.",
        headers={"Retry-After": "3600"},
    )
