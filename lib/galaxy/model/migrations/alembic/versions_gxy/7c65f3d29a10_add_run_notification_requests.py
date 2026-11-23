"""Add durable notification requests for tool and workflow runs.

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


def upgrade() -> None:
    create_table(
        "run_notification_request",
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
        sa.Column(
            "workflow_invocation_id",
            sa.Integer,
            sa.ForeignKey("workflow_invocation.id", ondelete="CASCADE"),
            unique=True,
        ),
        sa.Column("attention_sent", sa.Boolean, nullable=False),
        sa.Column("completed", sa.Boolean, nullable=False),
        sa.CheckConstraint(
            "(job_id IS NOT NULL AND implicit_collection_jobs_id IS NULL AND workflow_invocation_id IS NULL) OR "
            "(job_id IS NULL AND implicit_collection_jobs_id IS NOT NULL AND workflow_invocation_id IS NULL) OR "
            "(job_id IS NULL AND implicit_collection_jobs_id IS NULL AND workflow_invocation_id IS NOT NULL)",
            name="ck_run_notification_request_target",
        ),
        sa.Index("ix_run_notification_request_pending", "completed", "id"),
    )


def downgrade() -> None:
    drop_table("run_notification_request")
