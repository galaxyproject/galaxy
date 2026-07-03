"""Add tool_index table for storing pre-computed tool index

Revision ID: f5a73c8b9d12
Revises: 28885b317f78
Create Date: 2026-01-25 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "f5a73c8b9d12"
down_revision = "28885b317f78"
branch_labels = None
depends_on = None

TABLE_NAME = "tool_index"


def upgrade():
    """Create tool_index table for storing pre-computed tool index.

    This table stores a serialized ToolIndex object that provides
    fast access to tool metadata for API responses without loading
    full tool sources.
    """
    create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version", sa.String(64), nullable=False, unique=True),
        sa.Column("data", sa.LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"), nullable=False),
        sa.Column("built_at", sa.DateTime, nullable=True),
        sa.Column("create_time", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column(
            "update_time",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade():
    drop_table(TABLE_NAME)
