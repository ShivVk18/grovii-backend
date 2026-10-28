"""Phase G: per-step timings on jobs (for dashboards and /metrics).

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("node_timings", postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column("jobs", "node_timings")
