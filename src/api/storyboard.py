from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from src.database import get_db
from src.config.dependencies_config import get_current_user

from src.models.users import User

from src.Schemas.storyboard_schema import (
    CreateStoryboardRequest,
    UpdateStoryboardRequest,
    StoryboardResponse
)

from src.services import storyboard_service


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
    status_code=status.HTTP_201_CREATED
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
# Get Single Storyboard
####################################################

@router.get(
    "/{storyboard_id}",
    response_model=StoryboardResponse
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