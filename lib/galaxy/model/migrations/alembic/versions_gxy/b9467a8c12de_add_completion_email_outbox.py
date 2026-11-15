"""Add leases for SMTP-only completion emails.

Revision ID: b9467a8c12de
Revises: 7c65f3d29a10
"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    create_index,
    drop_column,
    drop_index,
)

revision = "b9467a8c12de"
down_revision = "7c65f3d29a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column("notification", sa.Column("email_only", sa.Boolean, nullable=False, server_default=sa.false()))
    add_column("notification", sa.Column("email_claimed_at", sa.DateTime, nullable=True))
    create_index("ix_notification_completion_email", "notification", ["email_only", "email_claimed_at", "id"])


def downgrade() -> None:
    drop_index("ix_notification_completion_email", "notification")
    drop_column("notification", "email_claimed_at")
    drop_column("notification", "email_only")
