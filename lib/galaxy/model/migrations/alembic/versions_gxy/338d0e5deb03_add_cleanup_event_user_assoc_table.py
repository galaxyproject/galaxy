"""Add cleanup_event_user_assoc table

Revision ID: 338d0e5deb03
Revises: c44ae5f3dcf1
Create Date: 2025-07-02 13:59:34.849280

"""

import logging

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
    table_exists,
)

log = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "338d0e5deb03"
down_revision = "c44ae5f3dcf1"
branch_labels = None
depends_on = None

TABLE_NAME = "cleanup_event_user_association"


def upgrade():
    if not table_exists(TABLE_NAME, True):
        create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("create_time", sa.DateTime),
            sa.Column("cleanup_event_id", sa.Integer, sa.ForeignKey("cleanup_event.id"), index=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True),
        )
    else:
        log.info(f"Skipping revision script: table {TABLE_NAME} already exists")


def downgrade():
    drop_table(TABLE_NAME)
