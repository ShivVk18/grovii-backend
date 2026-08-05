from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.ai.graph import graph
from src.models.storyboard import Storyboard
from src.models.scenes import Scene
from src.repositories.storyboard_repository import (

    create_storyboard as repo_create_storyboard,

    get_storyboards as repo_get_storyboards,

    get_storyboard as repo_get_storyboard,

    update_storyboard as repo_update_storyboard,

    delete_storyboard as repo_delete_storyboard,

    get_storyboard_with_relations

)
from src.services.queue_service import storyboard_queue

from src.services.jobs_services import generate_storyboard_job
from src.Schemas.storyboard_schema import (
    CreateStoryboardRequest,
    UpdateStoryboardRequest
)

from src.models.jobs import Job
from src.repositories.job_repository import create_job
from src.repositories.job_repository import (
        update_queue_job_id
)



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

async def create_ai_storyboard(
        db,
        payload,
        user_id,
        background_tasks=None
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
        language=getattr(payload, "language", "English") or "English",

        status="pending"

    )



    storyboard = repo_create_storyboard(

            db,

            storyboard

    )


    job = Job(

    user_id=user_id,

    storyboard_id=storyboard.id

)
    
    
    job = create_job(

        db,

        job

)


    state = {

        "idea":payload.idea,

        "goal":payload.goal,

        "tone":payload.tone,

        "style":payload.style,

        "audience":payload.audience,

        "duration":payload.duration,

        "platform":payload.platform,

        "language":getattr(payload, "language", "English") or "English",


        "hook":"",

        "scenes":[],

        "script":"",


        "captions":[],

        "hashtags":[],

        "regenerated_hooks":[],

        "trends":{},


        "scene_music":[],

        "repurposed_content":{},


        "thumbnail_url":""

    }




    use_redis = False
    try:
        from src.services.redis_service import redis_client
        if redis_client.ping():
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


        "job_id":job.id,


        "storyboard_id":storyboard.id,


        "status":"pending"
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