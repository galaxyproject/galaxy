"""Username column unique constraint

Revision ID: d619fdfa6168
Revises: d2d8f51ebb7e
Create Date: 2024-07-02 13:13:10.325586
"""

from alembic import op

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.data_fixes.user_table_fixer import UsernameDeduplicator
from galaxy.model.migrations.util import (
    create_index,
    drop_index,
    index_exists,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "d619fdfa6168"
down_revision = "d2d8f51ebb7e"
branch_labels = None
depends_on = None

table_name = "galaxy_user"
column_name = "username"
index_name = build_index_name(table_name, [column_name])


def upgrade():
    with transaction():
        _fix_duplicate_usernames()
        # Existing databases may have an existing index we no longer need
        # New databases will not have that index, so we must check.
        if index_exists(index_name, table_name, False):
            drop_index(index_name, table_name)
        # Create a UNIQUE index
        create_index(index_name, table_name, [column_name], unique=True)


def downgrade():
    with transaction():
        drop_index(index_name, table_name)
        # Restore a non-unique index
        create_index(index_name, table_name, [column_name])


def _fix_duplicate_usernames():
    """Fix records with duplicate usernames"""
    connection = op.get_bind()
    UsernameDeduplicator(connection).run()
