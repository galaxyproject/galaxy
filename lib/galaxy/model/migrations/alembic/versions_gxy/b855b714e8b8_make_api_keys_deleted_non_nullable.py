"""make api_keys deleted non nullable

Revision ID: b855b714e8b8
Revises: 3356bc2ecfc4
Create Date: 2023-04-19 18:41:13.500332

"""

import sqlalchemy as sa
from alembic import op

from galaxy.model.migrations.util import (
    alter_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "b855b714e8b8"
down_revision = "3356bc2ecfc4"
branch_labels = None
depends_on = None


table_name = "api_keys"
column_name = "deleted"


def upgrade():
    with transaction():
        # Update any existing rows with a deleted=NULL value to be deleted=True.
        # This will expire any existing API keys that didn't have a deleted value set.
        table = sa.sql.table(table_name, sa.Column(column_name, sa.Boolean(), nullable=True))
        op.execute(table.update().where(table.c.deleted.is_(None)).values(deleted=True))

        # Make the column non-nullable.
        alter_column(table_name, column_name, existing_type=sa.Boolean(), nullable=False, server_default=sa.false())


def downgrade():
    alter_column(table_name, column_name, existing_type=sa.Boolean(), nullable=True, server_default=None)
