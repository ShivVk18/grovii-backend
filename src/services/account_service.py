"""Data export and account deletion (Phase F, privacy).

Deletion removes every row tied to the user explicitly, in dependency order, so
it does not rely on ORM cascades being configured on each relationship.
"""
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, selectinload

from src.models.caption import Caption
from src.models.hashtag import Hashtag
from src.models.hook import Hook
from src.models.jobs import Job, JobStatus
from src.models.music import MusicSuggestion
from src.models.repurpose import RepurposeContent
from src.models.scenes import Scene
from src.models.sessions import UserSession
from src.models.storyboard import Storyboard
from src.models.subscription import UserSubscription
from src.models.trend import Trend
from src.models.users import User

logger = logging.getLogger("grovii.account")

STORYBOARD_CHILDREN = (Scene, Caption, Hashtag, Hook, MusicSuggestion, Trend, RepurposeContent)

# Internal columns that are never exported.
_SKIP = {"hashed_password", "error_message", "error", "internal_error"}


def _row(obj) -> dict[str, Any]:
    out = {}
    for col in obj.__table__.columns:
        if col.key in _SKIP:
            continue
        value = getattr(obj, col.key)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, "value"):  # enums
            value = value.value
        out[col.key] = value
    return out


def export_user_data(db: Session, user_id: str) -> dict[str, Any]:
    user = db.get(User, user_id)
    storyboards = (
        db.query(Storyboard)
        .options(*(selectinload(getattr(Storyboard, rel)) for rel in
                   ("scenes", "captions", "hashtags", "hooks", "music", "trends", "repurpose")))
        .filter(Storyboard.user_id == user_id)
        .order_by(Storyboard.created_at)
        .all()
    )
    jobs = db.query(Job).filter(Job.user_id == user_id).order_by(Job.created_at).all()
    sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()

    def storyboard(sb: Storyboard) -> dict[str, Any]:
        data = _row(sb)
        for rel in ("scenes", "captions", "hashtags", "hooks", "music", "trends"):
            data[rel] = [_row(x) for x in getattr(sb, rel)]
        data["repurpose"] = _row(sb.repurpose) if sb.repurpose else None
        return data

    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "account": _row(user),
        "storyboards": [storyboard(sb) for sb in storyboards],
        "generations": [_row(j) for j in jobs],
        "sign_ins": [{"created_at": s.created_at.isoformat(), "expires_at": s.expires_at.isoformat(),
                      "revoked_at": s.revoked_at.isoformat() if s.revoked_at else None} for s in sessions],
    }


def _cancel_queued_jobs(db: Session, user_id: str) -> None:
    """Remove this user's waiting jobs from the queue (best effort)."""
    try:
        from rq.job import Job as RQJob

        from src.services.redis_service import redis_client

        ids = [j.id for j in db.query(Job.id).filter(
            Job.user_id == user_id, Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))]
        for job_id in ids:
            try:
                RQJob.fetch(job_id, connection=redis_client).cancel()
            except Exception:  # noqa: BLE001 - already gone or running
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not cancel queued jobs on account deletion: %s", type(e).__name__)


def delete_user_data(db: Session, user_id: str) -> None:
    """Delete the user and everything they own, in one transaction. A worker
    still running one of their jobs finds the job gone and stops."""
    _cancel_queued_jobs(db, user_id)
    sb_ids = [i for (i,) in db.query(Storyboard.id).filter(Storyboard.user_id == user_id)]
    try:
        if sb_ids:
            for model in STORYBOARD_CHILDREN:
                db.query(model).filter(model.storyboard_id.in_(sb_ids)).delete(synchronize_session=False)
        db.query(Job).filter(Job.user_id == user_id).delete(synchronize_session=False)
        db.query(Storyboard).filter(Storyboard.user_id == user_id).delete(synchronize_session=False)
        db.query(UserSubscription).filter(UserSubscription.user_id == user_id).delete(synchronize_session=False)
        db.query(UserSession).filter(UserSession.user_id == user_id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info("Account deleted (%d storyboards)", len(sb_ids))
