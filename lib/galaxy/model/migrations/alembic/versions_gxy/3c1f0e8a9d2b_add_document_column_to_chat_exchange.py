"""add document column to chat_exchange

Revision ID: 3c1f0e8a9d2b
Revises: b9467a8c12de
Create Date: 2026-10-19 12:00:00.000000

"""

from sqlalchemy import Column

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "3c1f0e8a9d2b"
down_revision = "b9467a8c12de"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "chat_exchange"
column_name = "document"


def upgrade() -> None:
    add_column(table_name, Column(column_name, JSONType, nullable=True))


def downgrade() -> None:
    drop_column(table_name, column_name)
