"""add display_name column to galaxy_user

Revision ID: 64d49ad328d4
Revises: e96dd6fd5863
Create Date: 2026-08-13 10:00:00.000000

"""

from sqlalchemy import Column

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "64d49ad328d4"
down_revision = "e96dd6fd5863"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "galaxy_user"
column_name = "display_name"


def upgrade():
    add_column(table_name, Column(column_name, TrimmedString(255), nullable=True))


def downgrade():
    drop_column(table_name, column_name)
