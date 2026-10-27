"""Credit refunds for failed generation jobs."""
import logging

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.models.jobs import Job
from src.models.users import User

logger = logging.getLogger("grovii.credits")

# Error codes from the LLM provider that mean the user's own input was refused
# (for example by the provider's safety system). These are not refunded.
USER_FAULT_CODES = {"content_policy_violation", "content_filter"}


def is_user_fault(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    if code in USER_FAULT_CODES:
        return True
    body = getattr(exc, "body", None)
    if isinstance(body, dict) and body.get("code") in USER_FAULT_CODES:
        return True
    return False


def refund_job_credits(db: Session, job_id: str) -> bool:
    """Give back the credits charged for a job, at most once.

    The guarded UPDATE flips `credits_refunded` only if it is still false, so two
    concurrent callers (for example a failing worker and the Phase C reaper)
    cannot both refund. Returns True if this call did the refund.
    """
    try:
        row = db.execute(
            update(Job)
            .where(Job.id == job_id, Job.credits_charged > 0, Job.credits_refunded.is_(False))
            .values(credits_refunded=True)
            .returning(Job.user_id, Job.credits_charged)
        ).first()
        if row is None:
            db.rollback()
            return False
        db.execute(
            update(User).where(User.id == row.user_id).values(credits=User.credits + row.credits_charged)
        )
        db.commit()
        logger.info("Refunded %s credit(s) for job %s", row.credits_charged, job_id)
        return True
    except Exception:
        db.rollback()
        raise
