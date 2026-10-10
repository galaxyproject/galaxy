"""Username column unique constraint

Revision ID: 3b0a43f181af
Revises: 1b5bf427db25
Create Date: 2026-10-07 12:00:00.000000

"""

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    create_index,
    drop_index,
    index_exists,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "3b0a43f181af"
down_revision = "1b5bf427db25"
branch_labels = None
depends_on = None

table_name = "galaxy_user"
column_name = "username"
index_name = build_index_name(table_name, [column_name])


def upgrade() -> None:
    with transaction():
        if index_exists(index_name, table_name, True):
            drop_index(index_name, table_name)
        create_index(index_name, table_name, [column_name], unique=True)


def downgrade() -> None:
    with transaction():
        drop_index(index_name, table_name)
        create_index(index_name, table_name, [column_name])
