"""add chat_exchange notebook_id FK

Revision ID: da6ae3337444
Revises: b75f0f4dbcd4
Create Date: 2026-02-17

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    create_foreign_key,
    create_index,
    drop_column,
    drop_constraint,
    drop_index,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "da6ae3337444"
down_revision = "b75f0f4dbcd4"
branch_labels = None
depends_on = None


def upgrade():
    with transaction():
        add_column("chat_exchange", sa.Column("notebook_id", sa.Integer, nullable=True))
        create_index("ix_chat_exchange_notebook_id", "chat_exchange", ["notebook_id"])
        create_foreign_key(
            "chat_exchange_notebook_id_fkey",
            "chat_exchange",
            "history_notebook",
            ["notebook_id"],
            ["id"],
        )


def downgrade():
    with transaction():
        drop_constraint("chat_exchange_notebook_id_fkey", "chat_exchange")
        drop_index("ix_chat_exchange_notebook_id", "chat_exchange")
        drop_column("chat_exchange", "notebook_id")
