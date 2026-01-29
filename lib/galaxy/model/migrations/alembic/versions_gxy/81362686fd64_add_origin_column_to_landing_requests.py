"""Add origin column to landing request tables

Revision ID: 81362686fd64
Revises: c0959ad462b2
Create Date: 2025-09-26 12:39:25.000000

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "81362686fd64"
down_revision = "c0959ad462b2"
branch_labels = None
depends_on = None

# database object names used in this revision
tool_table_name = "tool_landing_request"
workflow_table_name = "workflow_landing_request"
column_name = "origin"


def upgrade():
    # Add origin column to tool_landing_request table
    column = sa.Column(
        column_name,
        sa.String(255),
        nullable=True,
        default=None,
    )
    add_column(tool_table_name, column)

    # Add origin column to workflow_landing_request table
    column = sa.Column(
        column_name,
        sa.String(255),
        nullable=True,
        default=None,
    )
    add_column(workflow_table_name, column)


def downgrade():
    # Drop origin column from both tables
    drop_column(tool_table_name, column_name)
    drop_column(workflow_table_name, column_name)
