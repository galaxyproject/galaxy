"""Add not-null constraints to user_role_association

Revision ID: 1fdd615f2cdb
Revises: 349dd9d9aac9
Create Date: 2024-09-09 21:28:11.987054

"""

from alembic import op

from galaxy.model.migrations.data_fixes.association_table_fixer import UserRoleAssociationNullFix
from galaxy.model.migrations.util import (
    alter_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "1fdd615f2cdb"
down_revision = "349dd9d9aac9"
branch_labels = None
depends_on = None

table_name = "user_role_association"


def upgrade():
    with transaction():
        _remove_records_with_nulls()
        alter_column(table_name, "user_id", nullable=False)
        alter_column(table_name, "role_id", nullable=False)


def downgrade():
    with transaction():
        alter_column(table_name, "user_id", nullable=True)
        alter_column(table_name, "role_id", nullable=True)


def _remove_records_with_nulls():
    """Remove associations having null as user_id or role_id"""
    connection = op.get_bind()
    UserRoleAssociationNullFix(connection).run()
