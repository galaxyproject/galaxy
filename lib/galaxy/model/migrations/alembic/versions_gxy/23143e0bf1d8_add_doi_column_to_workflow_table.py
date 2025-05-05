"""Add doi column to workflow table

Revision ID: 23143e0bf1d8
Revises: 71eeb8d91f92
Create Date: 2025-04-16 13:19:04.848395

"""

from sqlalchemy import (
    Column,
    JSON,
)

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "b964490175fd"
down_revision = "71eeb8d91f92"
branch_labels = None
depends_on = None

table_name = "workflow"
column_name = "doi"


def upgrade():
    add_column(table_name, Column(column_name, JSON))


def downgrade():
    drop_column(table_name, column_name)
