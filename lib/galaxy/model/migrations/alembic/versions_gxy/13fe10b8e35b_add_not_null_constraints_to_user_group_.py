"""Add not-null constraints to user_group_association

Revision ID: 13fe10b8e35b
Revises: 56ddf316dbd0
Create Date: 2024-09-09 21:26:26.032842

"""

from alembic import op

from galaxy.model.migrations.data_fixes.association_table_fixer import UserGroupAssociationNullFix
from galaxy.model.migrations.util import (
    alter_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "13fe10b8e35b"
down_revision = "56ddf316dbd0"
branch_labels = None
depends_on = None

table_name = "user_group_association"


def upgrade():
    with transaction():
        _remove_records_with_nulls()
        alter_column(table_name, "user_id", nullable=False)
        alter_column(table_name, "group_id", nullable=False)


def downgrade():
    with transaction():
        alter_column(table_name, "user_id", nullable=True)
        alter_column(table_name, "group_id", nullable=True)


def _remove_records_with_nulls():
    """Remove associations having null as user_id or group_id"""
    connection = op.get_bind()
    UserGroupAssociationNullFix(connection).run()
