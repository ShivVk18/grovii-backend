from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.ai.graph import graph
from src.api.errors import AppError
from src.config import limits
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
from src.services.jobs_services import generate_storyboard_job
from src.services.queue_service import storyboard_queue
from src.services.spend_service import ensure_daily_budget_available


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
                Job.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),
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
            status="pending",
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


async def create_ai_storyboard(
        db,
        payload,
        user_id,
        background_tasks=None
):
    storyboard, job = reserve_generation(db, payload, user_id)


    raw_duration = getattr(payload, "duration", 30)
    if isinstance(raw_duration, str):
        import re
        digits = re.findall(r"\d+", raw_duration)
        parsed_duration = int(digits[0]) if digits else 30
    else:
        parsed_duration = int(raw_duration or 30)

    state = {
        "idea": payload.idea,
        "goal": payload.goal,
        "tone": payload.tone,
        "style": payload.style,
        "audience": payload.audience,
        "duration": parsed_duration,
        "platform": payload.platform,
        "language": getattr(payload, "language", "English") or "English",
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

    use_redis = False
    try:
        from rq import Worker

        from src.services.redis_service import redis_client
        if redis_client.ping():
            workers = Worker.all(connection=redis_client)
            active_workers = [
                w for w in workers
                if "storyboard_queue" in [q.name for q in w.queues]
                and w.get_state() != "dead"
            ]
            if active_workers:
                rq_job = storyboard_queue.enqueue(
                    generate_storyboard_job,
                    state,
                    storyboard.id,
                    job.id
                )
                update_queue_job_id(
                    db,
                    job,
                    rq_job.id
                )
                use_redis = True
    except Exception:
        use_redis = False

    if not use_redis:
        if background_tasks is not None:
            background_tasks.add_task(
                generate_storyboard_job,
                state,
                storyboard.id,
                job.id
            )
        else:
            import asyncio
            asyncio.create_task(asyncio.to_thread(
                generate_storyboard_job,
                state,
                storyboard.id,
                job.id
            )) 

    return {
        "job_id": job.id,
        "storyboard_id": storyboard.id,
        "status": "pending"
    }

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