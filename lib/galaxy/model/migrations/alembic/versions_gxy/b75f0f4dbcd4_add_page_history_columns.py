"""add page history columns

Revision ID: b75f0f4dbcd4
Revises: f5e9e4bca542
Create Date: 2025-01-06

"""

import sqlalchemy as sa

from galaxy.model.custom_types import TrimmedString
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
revision = "b75f0f4dbcd4"
down_revision = "f5e9e4bca542"
branch_labels = None
depends_on = None


def upgrade():
    with transaction():
        # Page provenance: workflow invocation source
        add_column("page", sa.Column("source_invocation_id", sa.Integer, nullable=True))
        create_index("ix_page_source_invocation_id", "page", ["source_invocation_id"])
        create_foreign_key(
            "page_source_invocation_id_fkey",
            "page",
            "workflow_invocation",
            ["source_invocation_id"],
            ["id"],
        )

        # Page ↔ History association (replaces history_notebook)
        add_column("page", sa.Column("history_id", sa.Integer, nullable=True))
        create_index("ix_page_history_id", "page", ["history_id"])
        create_foreign_key(
            "page_history_id_fkey",
            "page",
            "history",
            ["history_id"],
            ["id"],
        )

        # PageRevision edit tracking
        add_column("page_revision", sa.Column("edit_source", TrimmedString(16), nullable=True))

        # ChatExchange ↔ Page association (replaces notebook_id)
        add_column("chat_exchange", sa.Column("page_id", sa.Integer, nullable=True))
        create_index("ix_chat_exchange_page_id", "chat_exchange", ["page_id"])
        create_foreign_key(
            "chat_exchange_page_id_fkey",
            "chat_exchange",
            "page",
            ["page_id"],
            ["id"],
        )


def downgrade():
    with transaction():
        drop_constraint("chat_exchange_page_id_fkey", "chat_exchange")
        drop_index("ix_chat_exchange_page_id", "chat_exchange")
        drop_column("chat_exchange", "page_id")

        drop_column("page_revision", "edit_source")

        drop_constraint("page_history_id_fkey", "page")
        drop_index("ix_page_history_id", "page")
        drop_column("page", "history_id")

        drop_constraint("page_source_invocation_id_fkey", "page")
        drop_index("ix_page_source_invocation_id", "page")
        drop_column("page", "source_invocation_id")
