"""Add workflow_source and workflow_source_type column

Revision ID: a99a5b52ccb8
Revises: 7ffd33d5d144
Create Date: 2024-10-10 14:23:29.485113

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "a99a5b52ccb8"
down_revision = "7ffd33d5d144"
branch_labels = None
depends_on = None

table_name = "workflow_landing_request"
column_names = ["workflow_source", "workflow_source_type"]


def upgrade():
    with transaction():
        for column_name in column_names:
            add_column(table_name, sa.Column(column_name, sa.String(255), nullable=True))


def downgrade():
    with transaction():
        for column_name in column_names:
            drop_column(table_name, column_name)
