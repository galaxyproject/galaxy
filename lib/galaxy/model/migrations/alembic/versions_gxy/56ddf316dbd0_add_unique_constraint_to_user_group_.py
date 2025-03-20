"""Add unique constraint to user_group_association

Revision ID: 56ddf316dbd0
Revises: 1fdd615f2cdb
Create Date: 2024-09-09 16:10:37.081834

"""

from alembic import op

from galaxy.model.migrations.data_fixes.association_table_fixer import UserGroupAssociationDuplicateFix
from galaxy.model.migrations.util import (
    create_unique_constraint,
    drop_constraint,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "56ddf316dbd0"
down_revision = "1fdd615f2cdb"
branch_labels = None
depends_on = None

table_name = "user_group_association"
constraint_column_names = ["user_id", "group_id"]
unique_constraint_name = (
    "user_group_association_user_id_key"  # This is what the model's naming convention will generate.
)


def upgrade():
    with transaction():
        _remove_duplicate_records()
        create_unique_constraint(unique_constraint_name, table_name, constraint_column_names)


def downgrade():
    with transaction():
        drop_constraint(unique_constraint_name, table_name)


def _remove_duplicate_records():
    """Remove duplicate associations"""
    connection = op.get_bind()
    UserGroupAssociationDuplicateFix(connection).run()
