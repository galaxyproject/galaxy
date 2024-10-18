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
column_names = ["workflow_source", "workflow_source_type", "public"]
column_types = [sa.String(255), sa.String(255), sa.Boolean]
nullable_columns = [True, True, False]


def upgrade():
    with transaction():
        for column_name, column_type, nullable in zip(column_names, column_types, nullable_columns):
            add_column(workflow_table_name, sa.Column(column_name, column_type, nullable=nullable))
        add_column(tool_table_name, sa.Column("public", sa.Boolean))


def downgrade():
    with transaction():
        for column_name in column_names:
            if column_exists(workflow_table_name, column_name, True):
                drop_column(workflow_table_name, column_name)
        drop_column(tool_table_name, sa.Column("public", sa.Boolean))
