"""add dispatched column to notifications

Revision ID: 303a5583a030
Revises: 55f02fd8ab6c
Create Date: 2024-04-04 11:45:54.018829

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import (
    Boolean,
    Column,
)

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    drop_index,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "303a5583a030"
down_revision = "55f02fd8ab6c"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "notification"
column_name = "dispatched"
publication_time_column_name = "publication_time"
index_name = build_index_name(table_name, column_name)


def upgrade():
    with transaction():
        add_column(
            table_name,
            Column(column_name, Boolean(), index=True, nullable=False, default=False, server_default=sa.false()),
        )
        # Set as already dispatched any notifications older than the current time to avoid sending them again
        table = sa.sql.table(
            table_name,
            Column(column_name, Boolean()),
            Column(publication_time_column_name, sa.DateTime()),
        )
        op.execute(table.update().where(table.c.publication_time <= sa.func.now()).values(dispatched=True))


def downgrade():
    with transaction():
        drop_index(index_name, table_name)
        drop_column(table_name, column_name)
