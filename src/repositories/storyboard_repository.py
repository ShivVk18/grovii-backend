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
        # Status is set by job_lifecycle.transition() after this save.

        ################################################
        # Clean existing relations for idempotency
        ################################################
        db.query(Scene).filter(Scene.storyboard_id == storyboard.id).delete()
        db.query(Hook).filter(Hook.storyboard_id == storyboard.id).delete()
        db.query(Caption).filter(Caption.storyboard_id == storyboard.id).delete()
        db.query(Hashtag).filter(Hashtag.storyboard_id == storyboard.id).delete()
        db.query(MusicSuggestion).filter(MusicSuggestion.storyboard_id == storyboard.id).delete()
        db.query(Trend).filter(Trend.storyboard_id == storyboard.id).delete()
        db.query(RepurposeContent).filter(RepurposeContent.storyboard_id == storyboard.id).delete()

        ################################################
        # Scenes
        ################################################

        scenes = []
        for idx, scene in enumerate(state.get("scenes", [])):
            adv = scene.get("advanced")
            if not adv or not isinstance(adv, dict):
                adv = {
                    "camera_angle": scene.get("camera_angle"),
                    "camera_movement": scene.get("camera_movement"),
                    "lighting": scene.get("lighting"),
                    "transition": scene.get("transition"),
                    "music": scene.get("music_mood"),
                    "scene_prompt": scene.get("scene_prompt"),
                    "negative_prompt": scene.get("negative_prompt"),
                    "reference_prompt": scene.get("subject"),
                    "image_generation_prompt": scene.get("scene_prompt"),
                    "director_notes": scene.get("broll"),
                    "technical_settings": f"{scene.get('camera_angle', '')} {scene.get('camera_movement', '')}".strip()
                }

            w_show = scene.get("what_to_show") or scene.get("what_to_record") or scene.get("broll") or scene.get("subject") or "Record scene visual action."
            v_example = scene.get("voiceover_example") or scene.get("what_to_say") or scene.get("script_segment") or ""
            on_screen = scene.get("onscreen_text") or ""
            tip_val = scene.get("tips") or (", ".join(scene.get("dos", [])) if isinstance(scene.get("dos"), list) else "")
            emo_val = scene.get("emotion") or scene.get("music_mood") or ""

            scenes.append(
                Scene(
                    storyboard_id=storyboard.id,
                    scene_number=idx + 1,
                    title=scene.get("title"),
                    duration=scene.get("duration"),
                    what_to_show=w_show,
                    voiceover_example=v_example,
                    onscreen_text=on_screen,
                    what_to_record=w_show,
                    what_to_say=v_example,
                    tips=tip_val,
                    emotion=emo_val,
                    advanced=adv,
                    # Legacy fallback fields
                    script_segment=v_example,
                    scene_prompt=adv.get("scene_prompt") or scene.get("scene_prompt"),
                    negative_prompt=adv.get("negative_prompt") or scene.get("negative_prompt"),
                    camera_angle=adv.get("camera_angle") or scene.get("camera_angle"),
                    camera_movement=adv.get("camera_movement") or scene.get("camera_movement"),
                    lighting=adv.get("lighting") or scene.get("lighting"),
                    transition=adv.get("transition") or scene.get("transition"),
                    music_mood=adv.get("music") or scene.get("music_mood"),
                    subject=scene.get("subject"),
                    broll=scene.get("broll"),
                    dos=scene.get("dos"),
                    donts=scene.get("donts")
                )
            )
        db.add_all(scenes)

        ################################################
        # Hooks
        ################################################

        hooks = [
            Hook(
                storyboard_id=storyboard.id,
                hook=hook.get("hook") if isinstance(hook, dict) else str(hook),
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
                caption=caption.get("caption") if isinstance(caption, dict) else str(caption),
            )
            for caption in state.get("captions", [])
        ]
        db.add_all(captions)

        ################################################
        # Hashtags
        ################################################

        hashtags = []
        for tag in state.get("hashtags", []):
            tag_text = tag.get("hashtag") or tag.get("tag") or str(tag) if isinstance(tag, dict) else str(tag)
            hashtags.append(
                Hashtag(
                    storyboard_id=storyboard.id,
                    hashtag=tag_text,
                )
            )
        db.add_all(hashtags)

        ################################################
        # Music
        ################################################

        music = [
            MusicSuggestion(
                storyboard_id=storyboard.id,
                song_name=item.get("song_name"),
                artist=item.get("artist"),
                why_fits=item.get("why_fits"),
                best_scene=item.get("best_scene"),
                mood=item.get("mood"),
                platform_popularity=item.get("platform_popularity"),
                royalty_free_alt=item.get("royalty_free_alt"),
                trending_instagram=state.get("trending_instagram_audio", []),
                trending_tiktok=state.get("trending_tiktok_audio", []),
                trending_youtube=state.get("trending_youtube_shorts_audio", []),
                genre=item.get("genre") or item.get("mood") or "Trending Track"
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
                    content_gap=trend.get("content_gaps") or trend.get("content_gap"),
                    transitions=trend.get("transitions"),
                    sounds=trend.get("sounds"),
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
                    twitter=repurpose.get("twitter") or repurpose.get("twitter_thread"),
                    carousel=repurpose.get("carousel"),
                    blog=repurpose.get("blog"),
                    newsletter=repurpose.get("newsletter"),
                )
            )

        db.commit()
        db.refresh(storyboard)
        return storyboard

    except Exception as e:
        db.rollback()
        raise e