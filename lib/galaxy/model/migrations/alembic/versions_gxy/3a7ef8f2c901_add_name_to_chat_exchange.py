"""add name to chat_exchange

Revision ID: 3a7ef8f2c901
Revises: 28885b317f78
Create Date: 2026-06-26

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "3a7ef8f2c901"
down_revision = "28885b317f78"
branch_labels = None
depends_on = None


def upgrade():
    with transaction():
        add_column("chat_exchange", sa.Column("name", sa.String(255), nullable=True))


def downgrade():
    with transaction():
        drop_column("chat_exchange", "name")
