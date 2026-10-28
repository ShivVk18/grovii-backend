
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from src.config.dependencies_config import get_current_user
from src.database import get_db
from src.models.users import User
from src.Schemas.storyboard_schema import (
    CreateStoryboardRequest,
    StoryboardDetailResponse,
    StoryboardResponse,
    UpdateStoryboardRequest,
)
from src.services import storyboard_service
from src.services.job_lifecycle import user_message_for
from src.services.rate_limit import limit_create, limit_generate

router = APIRouter(
    prefix="/storyboards",
    tags=["Storyboards"]
)

####################################################
# Create Storyboard
####################################################

@router.post(
    "",
    response_model=StoryboardResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_create)],
)
def create_storyboard(
        payload: CreateStoryboardRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    storyboard = storyboard_service.create_storyboard(
        db=db,
        payload=payload,
        user_id=current_user.id
    )

    return storyboard


####################################################
# Get Storyboards
####################################################

@router.get(
    "",
    response_model=list[StoryboardResponse]
)
def get_storyboards(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return storyboard_service.get_storyboards(
        db=db,
        user_id=current_user.id
    )


####################################################
# Job routes. Declared BEFORE /{storyboard_id}: FastAPI matches routes in
# order, so otherwise GET /storyboards/jobs is captured by /{storyboard_id}
# with storyboard_id="jobs" (bug API-01).
####################################################

@router.get(
    "/jobs/{job_id}"
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from src.repositories.job_repository import get_job as repo_get_job
    job = repo_get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view this job"
        )
    return {
        "id": job.id,
        "status": job.status,
        "storyboard_id": job.storyboard_id,
        "progress": job.progress,
        # User-safe text only; the internal error stays in the database.
        "error_message": user_message_for(job, job.storyboard),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None
    }


@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return storyboard_service.cancel_job(db=db, job_id=job_id, user_id=current_user.id)


@router.get(
    "/jobs"
)
def get_jobs_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from src.models.jobs import Job
    jobs = (
        db.query(Job)
        .options(joinedload(Job.storyboard))  # one query instead of one per job
        .filter(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    results = []
    for job in jobs:
        storyboard_title = "Unknown Storyboard"
        if job.storyboard:
            storyboard_title = job.storyboard.title
        
        results.append({
            "id": job.id,
            "status": job.status,
            "storyboard_id": job.storyboard_id,
            "storyboard_title": storyboard_title,
            "progress": job.progress,
            "error_message": user_message_for(job, job.storyboard),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None
        })
    return results


####################################################
# Get Single Storyboard
####################################################

@router.get(
    "/{storyboard_id}",
    response_model=StoryboardDetailResponse
)
def get_storyboard(
        storyboard_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return storyboard_service.get_storyboard(
        db=db,
        storyboard_id=storyboard_id,
        user_id=current_user.id
    )


####################################################
# Update Storyboard
####################################################

@router.patch(
    "/{storyboard_id}",
    response_model=StoryboardResponse
)
def update_storyboard(
        storyboard_id: str,
        payload: UpdateStoryboardRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return storyboard_service.update_storyboard(
        db=db,
        storyboard_id=storyboard_id,
        user_id=current_user.id,
        payload=payload
    )


####################################################
# Delete Storyboard
####################################################

@router.delete(
    "/{storyboard_id}"
)
def delete_storyboard(
        storyboard_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    storyboard_service.delete_storyboard(
        db=db,
        storyboard_id=storyboard_id,
        user_id=current_user.id
    )

    return {
        "message": "Storyboard deleted"
    
    }
    
   
@router.post(
    "/generate",
    dependencies=[Depends(limit_generate)],
)
def generate_ai_storyboard(
    payload: CreateStoryboardRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Plain `def` (not async): FastAPI runs it in a thread pool, so the locked
    # DB transaction in reserve_generation() never blocks the event loop.
    storyboard = storyboard_service.create_ai_storyboard(
        db=db,
        payload=payload,
        user_id=current_user.id,
        background_tasks=background_tasks
    )

    return storyboard
