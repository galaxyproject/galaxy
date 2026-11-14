"""add is_based_on column to workflow

Revision ID: fa5e55c14f6e
Revises: 64d49ad328d4
Create Date: 2026-11-11 10:00:00.000000

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
revision = "fa5e55c14f6e"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "workflow"
column_name = "is_based_on"


def upgrade() -> None:
    add_column(table_name, Column(column_name, JSON))


def downgrade() -> None:
    drop_column(table_name, column_name)
