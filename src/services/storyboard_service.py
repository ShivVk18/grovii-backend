from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.models.storyboard import Storyboard

from src.repositories.storyboard_repository import (
    create_storyboard as repo_create_storyboard,
    get_storyboards as repo_get_storyboards,
    get_storyboard as repo_get_storyboard,
    update_storyboard as repo_update_storyboard,
    delete_storyboard as repo_delete_storyboard
)

from src.Schemas.storyboard_schema import (
    CreateStoryboardRequest,
    UpdateStoryboardRequest
)


def create_storyboard(
        db: Session,
        payload: CreateStoryboardRequest,
        user_id: str
):
    storyboard = Storyboard(
        user_id=user_id,
        title=None,
        idea=payload.idea,
        goal=payload.goal,
        tone=payload.tone,
        style=payload.style,
        audience=payload.audience,
        duration=payload.duration,
        platform=payload.platform,
        status="draft"
    )

    return repo_create_storyboard(
        db,
        storyboard
    )


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