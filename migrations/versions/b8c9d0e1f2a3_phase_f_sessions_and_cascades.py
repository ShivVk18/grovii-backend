"""Phase F: server-side sessions and ON DELETE CASCADE for owned data.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
import sqlalchemy as sa
from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None

# (table, column, referenced table)
FKS = [
    ("storyboards", "user_id", "users"),
    ("scenes", "storyboard_id", "storyboards"),
    ("captions", "storyboard_id", "storyboards"),
    ("hashtags", "storyboard_id", "storyboards"),
    ("hooks", "storyboard_id", "storyboards"),
    ("music", "storyboard_id", "storyboards"),
    ("repurpose", "storyboard_id", "storyboards"),
    ("trends", "storyboard_id", "storyboards"),
    ("jobs", "user_id", "users"),
    ("jobs", "storyboard_id", "storyboards"),
    ("user_subscriptions", "user_id", "users"),
]


def _recreate(ondelete):
    for table, column, ref in FKS:
        name = f"{table}_{column}_fkey"
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, ref, [column], ["id"], ondelete=ondelete)


def upgrade():
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    _recreate("CASCADE")


def downgrade():
    _recreate(None)
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
