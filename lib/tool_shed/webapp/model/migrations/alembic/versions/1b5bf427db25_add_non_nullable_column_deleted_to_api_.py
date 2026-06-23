"""add non-nullable column deleted to API keys

Revision ID: 1b5bf427db25
Revises: 969bbf7bcc29
Create Date: 2024-05-29 21:53:53.516506

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import (
    Boolean,
    Column,
    false,
    ForeignKey,
    func,
    Integer,
    select,
)

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    drop_index,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "1b5bf427db25"
down_revision = "969bbf7bcc29"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "api_keys"
column_name = "deleted"
index_name = build_index_name(table_name, column_name)


def upgrade():
    with transaction():
        # Add a deleted column
        add_column(table_name, Column(column_name, Boolean(), nullable=False, index=True, server_default=false()))
        table = sa.sql.table(
            table_name,
            Column("id", Integer, primary_key=True),
            Column("user_id", ForeignKey("galaxy_user.id"), index=True),
            Column(column_name, Boolean, index=True, default=False),
        )
        # Set everything to deleted
        op.execute(table.update().values(deleted=True))
        # Select the latest api keys
        s = select(func.max(table.c.id)).group_by(table.c.user_id)
        # Set all of these api keys to not deleted
        op.execute(table.update().where(table.c.id.in_(s)).values(deleted=False))


def downgrade():
    with transaction():
        drop_index(index_name, table_name)
        drop_column(table_name, column_name)
