"""add workflow.source_metadata column

Revision ID: b182f655505f
Revises: e7b6dcb09efd
Create Date: 2022-03-14 12:56:57.067748

"""
from alembic import op
from sqlalchemy import Column

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    column_exists,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "b182f655505f"
down_revision = "e7b6dcb09efd"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "workflow"
column_name = "source_metadata"


def upgrade():
    if not column_exists(table_name, column_name):
        op.add_column(table_name, Column(column_name, JSONType))


def downgrade():
    drop_column(table_name, column_name)
