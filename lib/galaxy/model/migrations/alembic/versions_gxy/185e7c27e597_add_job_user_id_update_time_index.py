"""Add composite index on job(user_id, update_time).

Revision ID: 185e7c27e597
Revises: 64d49ad328d4
Create Date: 2026-10-27
"""

from galaxy.model.migrations.util import create_index, drop_index

revision = "185e7c27e597"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None


def upgrade():
    # Job listing queries filter by user_id and sort by update_time. Without this
    # composite index, a selective extra filter (e.g. a tool_id search) makes the
    # planner walk the whole update_time index instead of the user's own jobs.
    create_index("ix_job_user_id_update_time", "job", ["user_id", "update_time"])


def downgrade():
    drop_index("ix_job_user_id_update_time", "job")
