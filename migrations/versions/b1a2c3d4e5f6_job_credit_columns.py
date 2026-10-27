"""jobs: credits_charged and credits_refunded (Phase B, VULN-02)

Records how many credits each generation job took from the user and whether
they were given back, so refunds can be done exactly once.

Existing jobs get credits_charged = 0 (they were never charged), so they can
never be refunded.

Revision ID: b1a2c3d4e5f6
Revises: 36206729aa81
Create Date: 2026-10-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "36206729aa81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNS = {
    "credits_charged": lambda: sa.Column("credits_charged", sa.Integer(), nullable=False, server_default="0"),
    "credits_refunded": lambda: sa.Column("credits_refunded", sa.Boolean(), nullable=False, server_default=sa.false()),
}


def _existing_columns() -> set[str] | None:
    """Column names of `jobs`, or None if the table does not exist.

    The initial migration never created `jobs` (the app's startup create_all()
    does), so on a fresh database the table may be missing or may already have
    these columns. Both cases are handled; Phase C replaces this with a proper
    baseline migration.
    """
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
