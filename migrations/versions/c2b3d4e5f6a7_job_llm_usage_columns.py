"""jobs: LLM usage and estimated cost per job (Phase B)

Adds prompt_tokens, completion_tokens, llm_calls and cost_usd. All nullable:
NULL means "not recorded" (old jobs, or a job still running).

Revision ID: c2b3d4e5f6a7
Revises: b1a2c3d4e5f6
Create Date: 2026-10-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2b3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = {
    "prompt_tokens": lambda: sa.Column("prompt_tokens", sa.Integer(), nullable=True),
    "completion_tokens": lambda: sa.Column("completion_tokens", sa.Integer(), nullable=True),
    "llm_calls": lambda: sa.Column("llm_calls", sa.Integer(), nullable=True),
    "cost_usd": lambda: sa.Column("cost_usd", sa.Numeric(12, 6), nullable=True),
}


def _existing_columns() -> set[str] | None:
    # See b1a2c3d4e5f6: `jobs` may be missing from the Alembic history on a
    # fresh database (created by the app's create_all instead).
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("jobs"):
        return None
    return {c["name"] for c in inspector.get_columns("jobs")}


def upgrade() -> None:
    existing = _existing_columns()
    if existing is None:
        return
    for name, column in COLUMNS.items():
        if name not in existing:
            op.add_column("jobs", column())


def downgrade() -> None:
    existing = _existing_columns()
    if existing is None:
        return
    for name in reversed(list(COLUMNS)):
        if name in existing:
            op.drop_column("jobs", name)
