"""Add Notification Table

Revision ID: f6fb225c05ab
Revises: b182f655505f
Create Date: 2022-07-12 18:34:56.156814

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6fb225c05ab"
down_revision = "186d4835587b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_push",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("create_time", sa.DateTime),
        sa.Column("update_time", sa.DateTime),
        sa.Column("message_text", sa.String(500), index=True),
        sa.Column("deleted", sa.Boolean, index=True, default=False),
    )

    op.create_table(
        "user_notification_association",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True),
        sa.Column("notification_id", sa.Integer, sa.ForeignKey("notification_push.id"), index=True),
        sa.Column("create_time", sa.DateTime),
        sa.Column("update_time", sa.DateTime),
        sa.Column("status_seen", sa.Boolean, index=True, default=False),
    )


def downgrade():
    op.drop_table("user_notification_association")
    op.drop_table("notification_push")
