"""add non-nullable column deleted to API keys

Revision ID: 1b5bf427db25
Revises: 969bbf7bcc29
Create Date: 2024-05-29 21:53:53.516506

"""
import sqlalchemy as sa
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
revision = "1b5bf427db25"
down_revision = "969bbf7bcc29"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "api_keys"
column_name = "deleted"
index_name = build_index_name(table_name, column_name)


def upgrade():
    add_column(
        table_name, Column(column_name, Boolean(), default=False, index=True, nullable=False, server_default=sa.false())
    )


def downgrade():
    with transaction():
        drop_index(index_name, table_name)
        drop_column(table_name, column_name)
