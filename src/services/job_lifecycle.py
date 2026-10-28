"""One place that changes job + storyboard status together.

Before Phase C the job and its storyboard were updated separately, so a failed
job could leave its storyboard "pending" forever (RES-01). `transition()`
updates both rows in one commit, then (optionally) refunds the credit.

Status pairs used:
    job queued    -> storyboard queued      (waiting, or waiting for a retry)
    job running   -> storyboard running
    job completed -> storyboard completed | partial
    job failed    -> storyboard failed
    job cancelled -> storyboard cancelled
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models.jobs import Job, JobStatus
from src.models.storyboard import Storyboard
from src.services.credits_service import refund_job_credits

logger = logging.getLogger("grovii.jobs")

# Plain-language messages for creators. Internal error text never goes here.
REFUNDED = " Your credit has been refunded."
USER_MESSAGES = {
    "failed": "Something went wrong while generating your storyboard. Please try again." + REFUNDED,
    "scenes_missing": "We couldn't plan the scenes for this video. Please try again." + REFUNDED,
    "budget": "This idea needed more AI work than one generation allows. Try a simpler or shorter idea." + REFUNDED,
    "timeout": "Generation took too long and was stopped. Please try again." + REFUNDED,
    "queue_unavailable": "Generation couldn't start because our servers are busy. Please try again in a minute." + REFUNDED,
    "user_fault": "The AI provider declined this idea. Please rephrase it and try again.",
    "cancelled": "Generation was cancelled." + REFUNDED,
    "provider_down": "Our AI provider is having trouble right now, so we couldn't create your shoot plan."
                     " Please try again in a few minutes." + REFUNDED,
    "script_missing": "Your scenes are ready, but the voiceover script couldn't be written. "
                      "You can shoot from the scenes or generate again." + REFUNDED,
}

STORYBOARD_STATUS = {
    JobStatus.QUEUED: "queued",
    JobStatus.RUNNING: "running",
    JobStatus.FAILED: "failed",
    JobStatus.CANCELLED: "cancelled",
}


def transition(
    db: Session,
    job_id: str,
    job_status: JobStatus,
    *,
    storyboard_status: str | None = None,
    reason: str | None = None,
    internal_error: str | None = None,
    refund: bool = False,
) -> None:
    """Set job + storyboard status in one commit; refund afterwards if asked.

    `reason` is shown to the creator; `internal_error` is stored on the job
    for developers and never returned by the API.
    """
    now = datetime.now(timezone.utc)
    try:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("transition: job %s not found", job_id)
            return
        job.status = job_status
        if internal_error is not None:
            job.error_message = internal_error[:2000]
        if job_status == JobStatus.RUNNING:
            job.started_at = now
        if job_status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.completed_at = now
            if job_status == JobStatus.COMPLETED:
                job.progress = 100
        sb = db.get(Storyboard, job.storyboard_id)
        if sb is not None:
            sb.status = storyboard_status or STORYBOARD_STATUS.get(job_status, "completed")
            sb.status_reason = reason
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info("Job %s -> %s (storyboard %s)", job_id, job_status.value, storyboard_status or "")
    if refund:
        refund_job_credits(db, job_id)


def user_message_for(job: Job, storyboard: Storyboard | None) -> str | None:
    """What the API shows as the job's error_message: never internal text."""
    if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
        return None
    if storyboard is not None and storyboard.status_reason:
        return storyboard.status_reason
    return USER_MESSAGES["failed"]
