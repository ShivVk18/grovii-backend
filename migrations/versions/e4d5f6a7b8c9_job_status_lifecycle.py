"""job status lifecycle: queued/running/completed/failed/cancelled + storyboard status_reason

Job enum labels PENDING -> QUEUED, PROCESSING -> RUNNING, adds CANCELLED.
Storyboard status 'pending' -> 'queued', 'processing' -> 'running'.
Adds storyboards.status_reason (plain-language reason shown to creators).

Downgrade maps back: cancelled jobs -> FAILED, partial/cancelled storyboards
-> completed/failed, and recreates the old enum type.

Revision ID: e4d5f6a7b8c9
Revises: d3c4e5f6a7b8
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4d5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "d3c4e5f6a7b8"
branch_labels = None
depends_on = None


def _labels(bind) -> list[str]:
    return [r[0] for r in bind.execute(sa.text(
        "select enumlabel from pg_enum e join pg_type t on t.oid=e.enumtypid "
        "where t.typname='jobstatus' order by enumsortorder"))]


def _recreate_enum(bind, labels: list[str], mapping: dict[str, str]) -> None:
    """Swap the jobstatus type for one with `labels`, translating values via `mapping`."""
    case = " ".join(f"when '{old}' then '{new}'" for old, new in mapping.items())
    bind.execute(sa.text("alter type jobstatus rename to jobstatus_old"))
    bind.execute(sa.text("create type jobstatus as enum (" + ", ".join(f"'{x}'" for x in labels) + ")"))
    bind.execute(sa.text(
        "alter table jobs alter column status type jobstatus using "
        f"(case status::text {case} else status::text end)::jobstatus"))
    bind.execute(sa.text("drop type jobstatus_old"))


def upgrade() -> None:
    bind = op.get_bind()
    labels = _labels(bind)
    if labels and labels != ["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]:
        _recreate_enum(bind, ["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"],
                       {"PENDING": "QUEUED", "PROCESSING": "RUNNING"})
    bind.execute(sa.text("update storyboards set status='queued' where status='pending'"))
    bind.execute(sa.text("update storyboards set status='running' where status='processing'"))
    if "status_reason" not in {c["name"] for c in sa.inspect(bind).get_columns("storyboards")}:
        op.add_column("storyboards", sa.Column("status_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_column("storyboards", "status_reason")
    bind.execute(sa.text("update storyboards set status='pending' where status='queued'"))
    bind.execute(sa.text("update storyboards set status='processing' where status='running'"))
    bind.execute(sa.text("update storyboards set status='completed' where status='partial'"))
    bind.execute(sa.text("update storyboards set status='failed' where status='cancelled'"))
    if _labels(bind):
        _recreate_enum(bind, ["PENDING", "PROCESSING", "COMPLETED", "FAILED"],
                       {"QUEUED": "PENDING", "RUNNING": "PROCESSING", "CANCELLED": "FAILED"})
