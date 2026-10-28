"""Phase D: scene timestamps, creator constraints, brief choice, music labels

scenes.start_seconds / end_seconds, storyboards.constraints (JSONB) and
storyboards.brief_choice, music.verified and music.licensing_note.
All nullable; existing rows keep NULL. Fully reversible.

Revision ID: a7b8c9d0e1f2
Revises: f5e6a7b8c9d0
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f5e6a7b8c9d0"
branch_labels = None
depends_on = None

COLUMNS = [
    ("scenes", sa.Column("start_seconds", sa.Integer(), nullable=True)),
    ("scenes", sa.Column("end_seconds", sa.Integer(), nullable=True)),
    ("storyboards", sa.Column("constraints", postgresql.JSONB(), nullable=True)),
    ("storyboards", sa.Column("brief_choice", sa.Text(), nullable=True)),
    ("music", sa.Column("verified", sa.Boolean(), nullable=True)),
    ("music", sa.Column("licensing_note", sa.Text(), nullable=True)),
]


def upgrade() -> None:
    for table, column in COLUMNS:
        op.add_column(table, column)


def downgrade() -> None:
    for table, column in reversed(COLUMNS):
        op.drop_column(table, column.name)
