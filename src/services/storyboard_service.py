import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from rq import Retry
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.ai.graph import graph
from src.api.errors import AppError
from src.config import jobs as job_config
from src.config import limits
from src.config.log_safety import safe_error
from src.config.logging_config import request_id_var
from src.models.jobs import Job, JobStatus
from src.models.storyboard import Storyboard
from src.models.users import User
from src.repositories.job_repository import update_queue_job_id
from src.repositories.storyboard_repository import (
    create_storyboard as repo_create_storyboard,
)
from src.repositories.storyboard_repository import (
    delete_storyboard as repo_delete_storyboard,
)
from src.repositories.storyboard_repository import get_storyboard as repo_get_storyboard
from src.repositories.storyboard_repository import get_storyboard_with_relations
from src.repositories.storyboard_repository import (
    get_storyboards as repo_get_storyboards,
)
from src.repositories.storyboard_repository import (
    update_storyboard as repo_update_storyboard,
)
from src.Schemas.storyboard_schema import (
    CreateStoryboardRequest,
    UpdateStoryboardRequest,
)
from src.services.job_lifecycle import USER_MESSAGES, transition
from src.services.jobs_services import generate_storyboard_job
from src.services.queue_service import storyboard_queue
from src.services.spend_service import ensure_daily_budget_available

logger = logging.getLogger("grovii.storyboards")


async  def generate_storyboard(payload):
    state = {
        "idea": payload.idea,
        "goal": payload.goal,
        "tone": payload.tone,
        "style": payload.style,
        "audience": payload.audience,
        "duration": payload.duration,
        "platform": payload.platform,
        "hook": "",
        "scenes": [],
        "script": "",
        "captions": [],
        "hashtags": [],
        "regenerated_hooks": [],
        "trends": {},
        "scene_music": [],
        "repurposed_content": {},
        "thumbnail_url": ""
    }

    result = await graph.ainvoke(state)
    return result

def reserve_generation(db: Session, payload, user_id: str):
    """Charge the user and create the storyboard + job in ONE transaction.

    The user's row is locked (SELECT ... FOR UPDATE) for the whole transaction,
    so concurrent requests from the same user run one after another: each one
    sees the credits and active-job count left by the previous one. Without the
    lock, two requests could both read "1 credit left" and both succeed.

    Raises AppError 402 (no credits) or 429 (too many active jobs); in both
    cases nothing is charged or created.
    """
    try:
        user = db.query(User).filter(User.id == user_id).with_for_update().one()

        active_since = datetime.now(timezone.utc) - timedelta(minutes=limits.ACTIVE_JOB_WINDOW_MINUTES)
        active = (
            db.query(func.count(Job.id))
            .filter(
                Job.user_id == user_id,
                Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
                Job.created_at >= active_since,
            )
            .scalar()
        )
        if active >= limits.MAX_ACTIVE_JOBS_PER_USER:
            raise AppError(
                429, "too_many_active_jobs",
                f"You already have {active} storyboards generating. "
                "Wait for one to finish, then try again.",
                headers={"Retry-After": "30"},
            )

        # Global LLM spend ceiling for today (503 if reached).
        ensure_daily_budget_available(db)

        cost = limits.CREDITS_PER_GENERATION
        if (user.credits or 0) < cost:
            raise AppError(
                402, "insufficient_credits",
                "You're out of credits, so a new storyboard can't be generated right now.",
                credits=user.credits or 0,
            )
        user.credits = (user.credits or 0) - cost

        storyboard = Storyboard(
            user_id=user_id,
            title=f"{payload.tone} Storyboard",
            idea=payload.idea,
            goal=payload.goal,
            tone=payload.tone,
            style=payload.style,
            audience=payload.audience,
            duration=payload.duration,
            platform=payload.platform,
            language=payload.language,
            constraints=payload.constraints() if hasattr(payload, "constraints") else None,
            status="queued",
        )
        db.add(storyboard)
        db.flush()
        job = Job(user_id=user_id, storyboard_id=storyboard.id, credits_charged=cost)
        db.add(job)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(storyboard)
    db.refresh(job)
    return storyboard, job


def _job_state(payload) -> dict:
    return {
        "idea": payload.idea,
        "goal": payload.goal,
        "tone": payload.tone,
        "style": payload.style,
        "audience": payload.audience,
        "duration": payload.duration,
        "platform": payload.platform,
        "language": payload.language,
        "faceless": getattr(payload, "faceless", False),
        "location": getattr(payload, "location", None),
        "equipment": getattr(payload, "equipment", None),
        "hook": "",
        "scenes": [],
        "script": "",
        "captions": [],
        "hashtags": [],
        "regenerated_hooks": [],
        "trends": {},
        "scene_music": [],
        "repurposed_content": {},
        "thumbnail_url": "",
    }


def _warn_if_no_worker() -> None:
    """Log (not fail) when no worker listens on the queue: the job stays queued
    and the reaper fails it after QUEUED_TIMEOUT_MINUTES if nobody picks it up."""
    try:
        from rq import Worker

        listening = [
            w for w in Worker.all(connection=storyboard_queue.connection)
            if storyboard_queue.name in w.queue_names() and w.get_state() != "dead"
        ]
        if not listening:
            logger.warning("No worker is listening on queue %r; job will wait", storyboard_queue.name)
    except Exception as e:  # noqa: BLE001 - diagnostics only
        logger.warning("Could not check workers: %s", e)


def create_ai_storyboard(db, payload, user_id, background_tasks=None):
    """Charge, create, then hand the job to the worker queue.

    Jobs always go to Redis. Running them inside the API process is allowed
    only when ALLOW_INPROCESS_JOBS is set (local development).
    """
    storyboard, job = reserve_generation(db, payload, user_id)
    state = _job_state(payload)

    if job_config.ALLOW_INPROCESS_JOBS:
        logger.warning("ALLOW_INPROCESS_JOBS is on: running job %s in the API process", job.id)
        if background_tasks is None:
            raise RuntimeError("in-process mode needs FastAPI BackgroundTasks")
        background_tasks.add_task(generate_storyboard_job, state, storyboard.id, job.id)
    else:
        try:
            rq_job = storyboard_queue.enqueue(
                generate_storyboard_job, state, storyboard.id, job.id,
                job_id=job.id,  # same id in Redis and Postgres: easy to trace, no duplicates
                job_timeout=job_config.JOB_TIMEOUT_SECONDS,
                # RQ rejects Retry(max=0); no retries means no Retry object.
                retry=(Retry(max=job_config.JOB_MAX_RETRIES, interval=job_config.JOB_RETRY_INTERVALS)
                       if job_config.JOB_MAX_RETRIES > 0 else None),
                failure_ttl=7 * 24 * 3600,
                meta={"request_id": request_id_var.get()},  # traced into the worker's logs
            )
        except Exception as e:  # noqa: BLE001 - Redis down or misconfigured
            logger.error("Could not enqueue job %s: %s", job.id, safe_error(e))
            transition(db, job.id, JobStatus.FAILED, reason=USER_MESSAGES["queue_unavailable"],
                       internal_error=f"enqueue failed: {type(e).__name__}: {e}", refund=True)
            raise AppError(503, "queue_unavailable", USER_MESSAGES["queue_unavailable"],
                           headers={"Retry-After": "60"}) from None
        update_queue_job_id(db, job, getattr(rq_job, "id", job.id))
        _warn_if_no_worker()

    return {
        "job_id": job.id,
        "storyboard_id": storyboard.id,
        "status": JobStatus.QUEUED.value,
    }


def cancel_job(db: Session, job_id: str, user_id: str) -> dict:
    """Cancel a job that has not started yet, and refund it."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).with_for_update().first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.QUEUED:
        db.rollback()
        raise AppError(409, "not_cancellable",
                       "This generation has already started or finished, so it can't be cancelled.")
    try:
        from rq.job import Job as RQJob

        RQJob.fetch(job.queue_job_id or job.id, connection=storyboard_queue.connection).cancel()
    except Exception as e:  # noqa: BLE001 - the DB status below still stops the worker
        logger.warning("Could not cancel RQ job %s: %s", job_id, e)
    transition(db, job_id, JobStatus.CANCELLED, reason=USER_MESSAGES["cancelled"], refund=True)
    return {"job_id": job_id, "status": JobStatus.CANCELLED.value}


def create_storyboard(
        db: Session,
        payload: CreateStoryboardRequest,
        user_id: str
):
    storyboard = Storyboard(
        user_id=user_id,
        title=f"{payload.tone} Storyboard",
        idea=payload.idea,
        goal=payload.goal,
        tone=payload.tone,
        style=payload.style,
        audience=payload.audience,
        duration=payload.duration,
        platform=payload.platform,
        status="created"
    )
    return repo_create_storyboard(db, storyboard)


def get_storyboards(
        db: Session,
        user_id: str
):
    return repo_get_storyboards(
        db,
        user_id
    )


def get_storyboard(
        db: Session,
        storyboard_id: str,
        user_id: str
):
    storyboard = get_storyboard_with_relations(
        db,
        storyboard_id,
        user_id
    )

    if not storyboard:
        raise HTTPException(
            status_code=404,
            detail="Storyboard not found"
        )

    return storyboard


def update_storyboard(
        db: Session,
        storyboard_id: str,
        user_id: str,
        payload: UpdateStoryboardRequest
):
    storyboard = repo_get_storyboard(
        db,
        storyboard_id,
        user_id
    )

    if not storyboard:
        raise HTTPException(
            status_code=404,
            detail="Storyboard not found"
        )

    update_data = payload.model_dump(exclude_unset=True)

    return repo_update_storyboard(
        db,
        storyboard,
        update_data
    )


def delete_storyboard(
        db: Session,
        storyboard_id: str,
        user_id: str
):
    storyboard = repo_get_storyboard(
        db,
        storyboard_id,
        user_id
    )

    if not storyboard:
        raise HTTPException(
            status_code=404,
            detail="Storyboard not found"
        )

    repo_delete_storyboard(
        db,
        storyboard
    )

    return True