"""indexes on every foreign-key column (DB-03)

Postgres does not index foreign keys automatically. Without these, loading a
storyboard's scenes/hooks/... and listing a user's storyboards or jobs scan
whole tables. Also adds (user_id, created_at) on storyboards and jobs, matching
the "my items, newest first" list queries, and (status, created_at) on jobs
for the reaper and the daily spend check.

Revision ID: f5e6a7b8c9d0
Revises: e4d5f6a7b8c9
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f5e6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "e4d5f6a7b8c9"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_captions_storyboard_id", "captions", ["storyboard_id"]),
    ("ix_hashtags_storyboard_id", "hashtags", ["storyboard_id"]),
    ("ix_hooks_storyboard_id", "hooks", ["storyboard_id"]),
    ("ix_music_storyboard_id", "music", ["storyboard_id"]),
    ("ix_repurpose_storyboard_id", "repurpose", ["storyboard_id"]),
    ("ix_scenes_storyboard_id", "scenes", ["storyboard_id"]),
    ("ix_trends_storyboard_id", "trends", ["storyboard_id"]),
    ("ix_jobs_storyboard_id", "jobs", ["storyboard_id"]),
    ("ix_jobs_user_id_created_at", "jobs", ["user_id", "created_at"]),
    ("ix_jobs_status_created_at", "jobs", ["status", "created_at"]),
    ("ix_storyboards_user_id_created_at", "storyboards", ["user_id", "created_at"]),
    ("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"]),
    ("ix_user_subscriptions_plan_id", "user_subscriptions", ["plan_id"]),
]


def upgrade() -> None:
    for name, table, cols in INDEXES:
        op.create_index(name, table, cols, if_not_exists=True)


def downgrade() -> None:
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table, if_exists=True)
