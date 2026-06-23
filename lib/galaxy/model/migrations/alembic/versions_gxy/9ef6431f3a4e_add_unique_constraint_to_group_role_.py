"""Add unique constraint to group_role_association

Revision ID: 9ef6431f3a4e
Revises: 13fe10b8e35b
Create Date: 2024-09-09 15:01:20.426534

"""

from alembic import op

from galaxy.model.migrations.data_fixes.association_table_fixer import GroupRoleAssociationDuplicateFix
from galaxy.model.migrations.util import (
    create_unique_constraint,
    drop_constraint,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "9ef6431f3a4e"
down_revision = "13fe10b8e35b"
branch_labels = None
depends_on = None

table_name = "group_role_association"
constraint_column_names = ["group_id", "role_id"]
unique_constraint_name = (
    "group_role_association_group_id_key"  # This is what the model's naming convention will generate.
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
    GroupRoleAssociationDuplicateFix(connection).run()
