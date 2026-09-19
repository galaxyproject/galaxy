"""Add index on tool_id column of job table

Revision ID: a4c3ef999ab5
Revises: 75348cfb3715
Create Date: 2025-02-05 14:55:13.348044

"""

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    create_index,
    drop_index,
)

# revision identifiers, used by Alembic.
revision = "a4c3ef999ab5"
down_revision = "75348cfb3715"
branch_labels = None
depends_on = None


table_name = "job"
column_name = "tool_id"
index_name = build_index_name(table_name, column_name)


def upgrade():
    create_index(index_name, table_name, [column_name])


def downgrade():
    drop_index(index_name, table_name)
