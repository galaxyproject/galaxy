"""Add tool source store tables (tool_index, tool_source_record)

Revision ID: f5a73c8b9d12
Revises: 28885b317f78
Create Date: 2026-01-25 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "f5a73c8b9d12"
down_revision = "28885b317f78"
branch_labels = None
depends_on = None

INDEX_TABLE_NAME = "tool_index"
SOURCE_TABLE_NAME = "tool_source_record"


def upgrade():
    """Create the tool source store's tables.

    ``tool_index`` stores a serialized ToolIndex object that provides fast
    access to tool metadata for API responses without loading full tool
    sources. ``tool_source_record`` stores the content-addressed tool
    sources themselves — separate from ``tool_source``, whose rows belong
    to the job-request path and carry a different payload contract.
    """
    create_table(
        INDEX_TABLE_NAME,
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
    create_table(
        SOURCE_TABLE_NAME,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("hash", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("source", sa.Text().with_variant(mysql.LONGTEXT(), "mysql"), nullable=False),
        sa.Column("source_class", sa.String(255)),
        sa.Column("tool_id", sa.String(255), index=True),
        sa.Column("tool_version", sa.String(255)),
        sa.Column("tool_dir", sa.Text, nullable=True),
        sa.Column("source_path", sa.Text, nullable=True),
        sa.Column("stored_at", sa.DateTime, nullable=True),
        sa.Column("source_metadata", JSONType, nullable=True),
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
    drop_table(SOURCE_TABLE_NAME)
    drop_table(INDEX_TABLE_NAME)
