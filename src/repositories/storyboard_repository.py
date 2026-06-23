from sqlalchemy.orm import Session
from uuid import UUID
from src.models.storyboard import Storyboard
from src.models.scenes import Scene
from typing import List
from sqlalchemy.orm import joinedload


def create_storyboard(db: Session, storyboard: Storyboard) -> Storyboard:
    db.add(storyboard)
    db.commit()
    db.refresh(storyboard)
    return storyboard


def get_storyboards(db: Session, user_id: str):
    return (
        db.query(Storyboard)
        .filter(
            Storyboard.user_id == user_id
        )
        .order_by(
            Storyboard.created_at.desc()
        )
        .all()
    )


def get_storyboard(
        db: Session,
        storyboard_id: str,
        user_id: str
):
    return (
        db.query(Storyboard)
        .filter(
            Storyboard.id == storyboard_id,
            Storyboard.user_id == user_id
        )
        .first()
    )


def update_storyboard(
        db: Session,
        storyboard: Storyboard,
        data: dict
) -> Storyboard:
    for key, value in data.items():
        setattr(
            storyboard,
            key,
            value
        )

    db.commit()
    db.refresh(storyboard)
    return storyboard


def delete_storyboard(
        db: Session,
        storyboard: Storyboard
):
    db.delete(storyboard)
    db.commit()
    return True


def save_scenes(
        db: Session,
        scenes: List[Scene]
):
    db.add_all(scenes)
    db.commit()

    for scene in scenes:
        db.refresh(scene)

    return scenes


def get_storyboard_with_scenes(
        db: Session,
        storyboard_id: str,
        user_id: str
):
    storyboard = (
        db.query(Storyboard)
        .options(
            joinedload(
                Storyboard.scenes
            )
        )
        .filter(
            Storyboard.id == storyboard_id,
            Storyboard.user_id == user_id
        )
        .first()
    )

    return storyboard