"""create oauth_device_authorization table

Revision ID: 8144eee26c2b
Revises: 64d49ad328d4
Create Date: 2026-11-10 10:00:00.000000

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "8144eee26c2b"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "oauth_device_authorization"


def upgrade() -> None:
    create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("create_time", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("device_code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("user_code", sa.String(16), nullable=False, unique=True),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("scope", sa.Text),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True),
        sa.Column("requesting_ip", sa.String(255)),
        sa.Column("last_polled_at", sa.DateTime),
    )


def downgrade() -> None:
    drop_table(table_name)
