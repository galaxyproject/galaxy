"""Drop Job.params column

Revision ID: a5c5455b849a
Revises: e382f8eb5e12
Create Date: 2025-10-15 16:13:14.778789

"""

from sqlalchemy import Column

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "a5c5455b849a"
down_revision = "e382f8eb5e12"
branch_labels = None
depends_on = None

table_name = "job"
column_name = "params"


def upgrade():
    drop_column(table_name, column_name)


def downgrade():
    add_column(table_name, Column(column_name, TrimmedString(255)))
