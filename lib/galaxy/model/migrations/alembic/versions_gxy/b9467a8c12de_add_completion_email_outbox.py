"""Distinguish SMTP-only completion emails from in-app notifications.

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
    create_index("ix_notification_completion_email", "notification", ["email_only", "dispatched", "id"])


def downgrade() -> None:
    drop_index("ix_notification_completion_email", "notification")
    drop_column("notification", "email_only")
