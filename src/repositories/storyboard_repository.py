from sqlalchemy.orm import Session, joinedload
from src.models.storyboard import Storyboard
from src.models.scenes import Scene
from src.models.hook import Hook
from src.models.caption import Caption
from src.models.hashtag import Hashtag
from src.models.music import MusicSuggestion
from src.models.trend import Trend
from src.models.repurpose import RepurposeContent
from typing import List


def create_storyboard(db: Session, storyboard: Storyboard) -> Storyboard:
    try:
        db.add(storyboard)
        db.commit()
        db.refresh(storyboard)
        return storyboard
    except Exception as e:
        db.rollback()
        raise e


def get_storyboards(db: Session, user_id: str):
    try:
        return (
            db.query(Storyboard)
            .filter(Storyboard.user_id == user_id)
            .order_by(Storyboard.created_at.desc())
            .all()
        )
    except Exception as e:
        raise e


def get_storyboard(db: Session, storyboard_id: str, user_id: str):
    try:
        return (
            db.query(Storyboard)
            .filter(
                Storyboard.id == storyboard_id,
                Storyboard.user_id == user_id
            )
            .first()
        )
    except Exception as e:
        raise e


def update_storyboard(db: Session, storyboard: Storyboard, data: dict) -> Storyboard:
    try:
        for key, value in data.items():
            setattr(storyboard, key, value)
        db.commit()
        db.refresh(storyboard)
        return storyboard
    except Exception as e:
        db.rollback()
        raise e


def delete_storyboard(db: Session, storyboard: Storyboard):
    try:
        db.delete(storyboard)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e


def get_storyboard_with_scenes(db: Session, storyboard_id: str, user_id: str):
    try:
        return (
            db.query(Storyboard)
            .options(joinedload(Storyboard.scenes))
            .filter(
                Storyboard.id == storyboard_id,
                Storyboard.user_id == user_id
            )
            .first()
        )
    except Exception as e:
        raise e


def mark_completed(db: Session, storyboard: Storyboard):
    try:
        storyboard.status = "completed"
        db.commit()
        db.refresh(storyboard)
        return storyboard
    except Exception as e:
        db.rollback()
        raise e


def mark_failed(db: Session, storyboard: Storyboard):
    try:
        storyboard.status = "failed"
        db.commit()
        return storyboard
    except Exception as e:
        db.rollback()
        raise e


def get_storyboard_with_relations(db: Session, storyboard_id: str, user_id: str):
    try:
        return (
            db.query(Storyboard)
            .options(
                joinedload(Storyboard.scenes),
                joinedload(Storyboard.captions),
                joinedload(Storyboard.hashtags),
                joinedload(Storyboard.hooks),
                joinedload(Storyboard.music),
                joinedload(Storyboard.trends),
                joinedload(Storyboard.repurpose),
            )
            .filter(
                Storyboard.id == storyboard_id,
                Storyboard.user_id == user_id
            )
            .first()
        )
    except Exception as e:
        raise e


def save_graph_result(db: Session, storyboard_id: str, state: dict):
    try:
        storyboard = (
            db.query(Storyboard)
            .filter(Storyboard.id == storyboard_id)
            .first()
        )

        if not storyboard:
            raise Exception("Storyboard not found")

        ################################################
        # Storyboard
        ################################################

        storyboard.hook = state.get("hook")
        storyboard.script = state.get("script")
        storyboard.status = "completed"

        ################################################
        # Scenes
        ################################################

        scenes = [
            Scene(
                storyboard_id=storyboard.id,
                scene_number=idx + 1,
                title=scene.get("title"),
                script_segment=scene.get("script_segment"),
                scene_prompt=scene.get("scene_prompt"),
                duration=scene.get("duration"),
            )
            for idx, scene in enumerate(state.get("scenes", []))
        ]
        db.add_all(scenes)

        ################################################
        # Hooks
        ################################################

        hooks = [
            Hook(
                storyboard_id=storyboard.id,
                hook=hook,
                selected=False,
            )
            for hook in state.get("regenerated_hooks", [])
        ]
        db.add_all(hooks)

        ################################################
        # Captions
        ################################################

        captions = [
            Caption(
                storyboard_id=storyboard.id,
                caption=caption.get("caption"),
            )
            for caption in state.get("captions", [])
        ]
        db.add_all(captions)

        ################################################
        # Hashtags
        ################################################

        hashtags = [
            Hashtag(
                storyboard_id=storyboard.id,
                hashtag=tag,
            )
            for tag in state.get("hashtags", [])
        ]
        db.add_all(hashtags)

        ################################################
        # Music
        ################################################

        music = [
            MusicSuggestion(
                storyboard_id=storyboard.id,
                genre=item.get("genre"),
                mood=item.get("mood"),
            )
            for item in state.get("scene_music", [])
        ]
        db.add_all(music)

        ################################################
        # Trends
        ################################################

        trend = state.get("trends")
        if trend:
            db.add(
                Trend(
                    storyboard_id=storyboard.id,
                    posting_time=trend.get("posting_time"),
                    editing_style=trend.get("editing_style"),
                )
            )

        ################################################
        # Repurpose
        ################################################

        repurpose = state.get("repurposed_content")
        if repurpose:
            db.add(
                RepurposeContent(
                    storyboard_id=storyboard.id,
                    linkedin=repurpose.get("linkedin"),
                    twitter=repurpose.get("twitter"),
                )
            )

        db.commit()
        db.refresh(storyboard)
        return storyboard

    except Exception as e:
        db.rollback()
        raise e