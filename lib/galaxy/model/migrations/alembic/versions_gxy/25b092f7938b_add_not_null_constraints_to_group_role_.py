"""Add not-null constraints to group_role_association

Revision ID: 25b092f7938b
Revises: 9ef6431f3a4e
Create Date: 2024-09-09 16:17:26.652865

"""

from alembic import op

from galaxy.model.migrations.data_fixes.association_table_fixer import GroupRoleAssociationNullFix
from galaxy.model.migrations.util import (
    alter_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "25b092f7938b"
down_revision = "9ef6431f3a4e"
branch_labels = None
depends_on = None

table_name = "group_role_association"


def upgrade():
    with transaction():
        _remove_records_with_nulls()
        alter_column(table_name, "group_id", nullable=True)
        alter_column(table_name, "role_id", nullable=False)


def downgrade():
    with transaction():
        alter_column(table_name, "group_id", nullable=True)
        alter_column(table_name, "role_id", nullable=True)


def _remove_records_with_nulls():
    """Remove associations having null as group_id or role_id"""
    connection = op.get_bind()
    GroupRoleAssociationNullFix(connection).run()
