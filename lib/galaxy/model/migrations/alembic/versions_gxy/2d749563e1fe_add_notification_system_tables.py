"""Add Notification System tables

Revision ID: 2d749563e1fe
Revises: b855b714e8b8
Create Date: 2023-03-02 15:16:36.737075

"""

import sqlalchemy as sa

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "2d749563e1fe"
down_revision = "b855b714e8b8"
branch_labels = None
depends_on = None

NOTIFICATION_TABLE_NAME = "notification"
USER_NOTIFICATION_ASSOC_TABLE_NAME = "user_notification_association"


def upgrade():
    with transaction():
        create_table(
            NOTIFICATION_TABLE_NAME,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("create_time", sa.DateTime),
            sa.Column("update_time", sa.DateTime),
            sa.Column("publication_time", sa.DateTime),
            sa.Column("expiration_time", sa.DateTime),
            sa.Column("source", sa.String(32), index=True),
            sa.Column("category", sa.String(64), index=True),
            sa.Column("variant", sa.String(16), index=True),
            sa.Column("content", JSONType),
        )

        create_table(
            USER_NOTIFICATION_ASSOC_TABLE_NAME,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True),
            sa.Column("notification_id", sa.Integer, sa.ForeignKey("notification.id"), index=True),
            sa.Column("seen_time", sa.DateTime, nullable=True),
            sa.Column("deleted", sa.Boolean, index=True, default=False),
            sa.Column("update_time", sa.DateTime),
        )


def downgrade():
    with transaction():
        drop_table(USER_NOTIFICATION_ASSOC_TABLE_NAME)
        drop_table(NOTIFICATION_TABLE_NAME)
