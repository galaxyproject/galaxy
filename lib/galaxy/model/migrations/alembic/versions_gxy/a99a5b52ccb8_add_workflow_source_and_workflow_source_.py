"""Add workflow_source and workflow_source_type and public column

Revision ID: a99a5b52ccb8
Revises: 7ffd33d5d144
Create Date: 2024-10-10 14:23:29.485113

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    column_exists,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "a99a5b52ccb8"
down_revision = "7ffd33d5d144"
branch_labels = None
depends_on = None

workflow_table_name = "workflow_landing_request"
tool_table_name = "tool_landing_request"


def drop_if_exists(table_name: str, column_name: str):
    if column_exists(table_name, column_name, True):
        drop_column(table_name, column_name)


def upgrade():
    with transaction():
        add_column(workflow_table_name, sa.Column("workflow_source", sa.String(255), nullable=True))
        add_column(workflow_table_name, sa.Column("workflow_source_type", sa.String(255), nullable=True))
        add_column(workflow_table_name, sa.Column("public", sa.Boolean, nullable=False))
        add_column(tool_table_name, sa.Column("public", sa.Boolean, nullable=False))


def downgrade():
    with transaction():
        drop_column(workflow_table_name, "workflow_source")
        drop_column(workflow_table_name, "workflow_source_type")
        # For test.galaxyproject.org which was deployed from PR branch that didn't contain public column
        drop_if_exists(workflow_table_name, "public")
        drop_if_exists(tool_table_name, "public")
