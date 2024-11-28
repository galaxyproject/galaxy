"""Remove unique constraint from role name, add not null constraint

Revision ID: 9a5207190a4d
Revises: a99a5b52ccb8
Create Date: 2024-10-08 14:08:28.418055

"""

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    alter_column,
    create_index,
    drop_index,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "9a5207190a4d"
down_revision = "a99a5b52ccb8"
branch_labels = None
depends_on = None


table_name = "role"
column_name = "name"
index_name = build_index_name(table_name, [column_name])


def upgrade():
    with transaction():
        drop_index(index_name, table_name)
        alter_column(table_name, column_name, nullable=False)
        create_index(index_name, table_name, [column_name])


def downgrade():
    with transaction():
        drop_index(index_name, table_name)
        alter_column(table_name, column_name, nullable=True)
        create_index(index_name, table_name, [column_name], unique=True)
