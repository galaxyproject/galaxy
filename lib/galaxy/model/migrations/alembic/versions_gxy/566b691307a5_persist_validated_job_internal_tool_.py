"""Persist validated job internal tool state.

Revision ID: 566b691307a5
Revises: 1d1d7bf6ac02
Create Date: 2025-09-30 04:48:19.727414

"""

from sqlalchemy import Column

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "566b691307a5"
down_revision = "1d1d7bf6ac02"
branch_labels = None
depends_on = None

table_name = "job"
column_name = "tool_state"


def upgrade():
    add_column(table_name, Column(column_name, JSONType))


def downgrade():
    drop_column(table_name, column_name)
