"""catch-up baseline: tables and columns that only ever existed via create_all()

The initial migration never created `jobs`, `subscription_plans` or
`user_subscriptions`, and the app's startup code added 18 columns with ad-hoc
ALTER TABLEs. This migration creates whatever is missing, so a fresh database
built only with `alembic upgrade head` matches the models. On an existing
database (where create_all() already made them) every step is skipped.

Downgrade removes only what this migration itself created, so it never drops
tables or columns that existed before it ran (recorded in a marker table).

Revision ID: d3c4e5f6a7b8
Revises: c2b3d4e5f6a7
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d3c4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "c2b3d4e5f6a7"
branch_labels = None
depends_on = None

MARKER = "_alembic_catch_up_created"

JOB_STATUS = postgresql.ENUM("QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED",
                             name="jobstatus", create_type=False)

COLUMNS = {
    "music": [
        sa.Column("song_name", sa.String()), sa.Column("artist", sa.String()),
        sa.Column("why_fits", sa.Text()), sa.Column("best_scene", sa.String()),
        sa.Column("platform_popularity", sa.String()), sa.Column("royalty_free_alt", sa.String()),
        sa.Column("trending_instagram", postgresql.JSONB()), sa.Column("trending_tiktok", postgresql.JSONB()),
        sa.Column("trending_youtube", postgresql.JSONB()),
    ],
    "scenes": [
        sa.Column("what_to_show", sa.Text()), sa.Column("voiceover_example", sa.Text()),
        sa.Column("onscreen_text", sa.String()), sa.Column("what_to_record", sa.Text()),
        sa.Column("what_to_say", sa.Text()), sa.Column("tips", sa.Text()),
        sa.Column("emotion", sa.String()), sa.Column("advanced", postgresql.JSONB()),
        sa.Column("scene_prompt", sa.Text()),
    ],
    "storyboards": [sa.Column("language", sa.String(), server_default="English")],
}


def _tables(table):
    if table == "subscription_plans":
        op.create_table("subscription_plans",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("features", sa.String()),
            sa.Column("is_active", sa.Boolean()))
    elif table == "user_subscriptions":
        op.create_table("user_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id")),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plans.id")),
            sa.Column("start_date", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("end_date", sa.DateTime()))
    elif table == "jobs":
        bind = op.get_bind()
        exists = bind.execute(sa.text("select 1 from pg_type where typname='jobstatus'")).scalar()
        if not exists:
            JOB_STATUS.create(bind)
        op.create_table("jobs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("status", JOB_STATUS, nullable=False),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("storyboard_id", sa.String(), sa.ForeignKey("storyboards.id"), nullable=False),
            sa.Column("queue_job_id", sa.String()),
            sa.Column("error_message", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            sa.Column("started_at", sa.DateTime()),
            sa.Column("progress", sa.Integer()),
            sa.Column("credits_charged", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("credits_refunded", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("prompt_tokens", sa.Integer()),
            sa.Column("completion_tokens", sa.Integer()),
            sa.Column("llm_calls", sa.Integer()),
            sa.Column("cost_usd", sa.Numeric(12, 6)))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    created = {"tables": [], "columns": []}
    for table in ("subscription_plans", "user_subscriptions", "jobs"):
        if not insp.has_table(table):
            _tables(table)
            created["tables"].append(table)
    for table, cols in COLUMNS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        for col in cols:
            if col.name not in existing:
                op.add_column(table, col.copy())
                created["columns"].append([table, col.name])
    op.create_table(MARKER, sa.Column("created", sa.Text()))
    op.get_bind().execute(sa.text(f"insert into {MARKER} values (:c)"), {"c": json.dumps(created)})


def downgrade() -> None:
    bind = op.get_bind()
    created = json.loads(bind.execute(sa.text(f"select created from {MARKER}")).scalar() or "{}")
    for table, column in reversed(created.get("columns", [])):
        op.drop_column(table, column)
    for table in reversed(created.get("tables", [])):
        op.drop_table(table)
        if table == "jobs":
            bind.execute(sa.text("drop type if exists jobstatus"))
    op.drop_table(MARKER)
