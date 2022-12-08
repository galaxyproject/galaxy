"""add column deleted to API keys

Revision ID: e0e3bb173ee6
Revises: 186d4835587b
Create Date: 2022-09-27 14:09:05.890227

"""
from alembic import op
from sqlalchemy import (
    Boolean,
    Column,
)

from galaxy.model.migrations.util import (
    column_exists,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "e0e3bb173ee6"
down_revision = "186d4835587b"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "api_keys"
column_name = "deleted"


def upgrade():
    if not column_exists(table_name, column_name):
        op.add_column(table_name, Column(column_name, Boolean(), default=False))


def downgrade():
    drop_column(table_name, column_name)
