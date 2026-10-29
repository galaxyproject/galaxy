"""Add unique constraint to user_role_association

Revision ID: 349dd9d9aac9
Revises: 1cf595475b58
Create Date: 2024-09-09 16:14:58.278850

"""

from alembic import op

from galaxy.model.migrations.data_fixes.association_table_fixer import UserRoleAssociationDuplicateFix
from galaxy.model.migrations.util import (
    create_unique_constraint,
    drop_constraint,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "349dd9d9aac9"
down_revision = "1cf595475b58"
branch_labels = None
depends_on = None

table_name = "user_role_association"
constraint_column_names = ["user_id", "role_id"]
unique_constraint_name = (
    "user_role_association_user_id_key"  # This is what the model's naming convention will generate.
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
    UserRoleAssociationDuplicateFix(connection).run()
