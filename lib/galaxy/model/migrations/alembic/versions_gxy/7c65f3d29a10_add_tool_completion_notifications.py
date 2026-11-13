"""Add durable tool completion notification requests.

Revision ID: 7c65f3d29a10
Revises: 64d49ad328d4
"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

revision = "7c65f3d29a10"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None


def upgrade():
    create_table(
        "tool_completion_notification",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("galaxy_user.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column(
            "history_id", sa.Integer, sa.ForeignKey("history.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("job.id", ondelete="CASCADE"), unique=True),
        sa.Column(
            "implicit_collection_jobs_id",
            sa.Integer,
            sa.ForeignKey("implicit_collection_jobs.id", ondelete="CASCADE"),
            unique=True,
        ),
        sa.Column("completed", sa.Boolean, nullable=False),
        sa.CheckConstraint(
            "(job_id IS NULL) != (implicit_collection_jobs_id IS NULL)", name="ck_tool_completion_notification_target"
        ),
        sa.Index("ix_tool_completion_notification_pending", "completed", "id"),
    )


def downgrade():
    drop_table("tool_completion_notification")
