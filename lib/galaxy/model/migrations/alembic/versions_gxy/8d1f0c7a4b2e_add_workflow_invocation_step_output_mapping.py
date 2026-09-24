"""add workflow invocation step output mapping

Revision ID: 8d1f0c7a4b2e
Revises: e96dd6fd5863
Create Date: 2026-09-09

"""

from sqlalchemy import Column

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    column_exists,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "8d1f0c7a4b2e"
down_revision = "e96dd6fd5863"
branch_labels = None
depends_on = None

table_name = "workflow_invocation_step"
column_name = "output_mapping"


def upgrade():
    if not column_exists(table_name, column_name, False):
        add_column(table_name, Column(column_name, JSONType))


def downgrade():
    drop_column(table_name, column_name)
