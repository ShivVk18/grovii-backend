"""Indexes declared in one place (created by migration f5e6a7b8c9d0).
Kept next to the models so create_all() and `alembic check` agree with the
migrations."""
from sqlalchemy import Index

from src.models.caption import Caption
from src.models.hashtag import Hashtag
from src.models.hook import Hook
from src.models.jobs import Job
from src.models.music import MusicSuggestion
from src.models.repurpose import RepurposeContent
from src.models.scenes import Scene
from src.models.storyboard import Storyboard
from src.models.subscription import UserSubscription
from src.models.trend import Trend

INDEXES = [
    Index("ix_captions_storyboard_id", Caption.storyboard_id),
    Index("ix_hashtags_storyboard_id", Hashtag.storyboard_id),
    Index("ix_hooks_storyboard_id", Hook.storyboard_id),
    Index("ix_music_storyboard_id", MusicSuggestion.storyboard_id),
    Index("ix_repurpose_storyboard_id", RepurposeContent.storyboard_id),
    Index("ix_scenes_storyboard_id", Scene.storyboard_id),
    Index("ix_trends_storyboard_id", Trend.storyboard_id),
    Index("ix_jobs_storyboard_id", Job.storyboard_id),
    Index("ix_jobs_user_id_created_at", Job.user_id, Job.created_at),
    Index("ix_jobs_status_created_at", Job.status, Job.created_at),
    Index("ix_storyboards_user_id_created_at", Storyboard.user_id, Storyboard.created_at),
    Index("ix_user_subscriptions_user_id", UserSubscription.user_id),
    Index("ix_user_subscriptions_plan_id", UserSubscription.plan_id),
]
