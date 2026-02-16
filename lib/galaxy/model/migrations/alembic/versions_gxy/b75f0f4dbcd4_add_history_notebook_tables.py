"""add history_notebook tables

Revision ID: b75f0f4dbcd4
Revises: 566b691307a5, b964490175fd
Create Date: 2025-01-06

"""

import sqlalchemy as sa

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrations.util import (
    add_column,
    create_foreign_key,
    create_index,
    create_table,
    drop_column,
    drop_constraint,
    drop_index,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "b75f0f4dbcd4"
down_revision = "566b691307a5"
branch_labels = None
depends_on = None

NOTEBOOK_TABLE = "history_notebook"
REVISION_TABLE = "history_notebook_revision"


def upgrade():
    with transaction():
        # Create notebook table first (without latest_revision_id FK)
        create_table(
            NOTEBOOK_TABLE,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("create_time", sa.DateTime),
            sa.Column("update_time", sa.DateTime),
            sa.Column(
                "history_id",
                sa.Integer,
                sa.ForeignKey("history.id"),
                nullable=False,
                index=True,
            ),  # No unique - multiple notebooks per history
            sa.Column("title", sa.Text),
            sa.Column("latest_revision_id", sa.Integer, index=True),
            sa.Column("deleted", sa.Boolean, default=False, index=True),
            sa.Column("purged", sa.Boolean, default=False, index=True),
        )

        # Create revision table with FK to notebook
        create_table(
            REVISION_TABLE,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("create_time", sa.DateTime),
            sa.Column("update_time", sa.DateTime),
            sa.Column(
                "notebook_id",
                sa.Integer,
                sa.ForeignKey("history_notebook.id"),
                index=True,
            ),
            sa.Column("content", sa.Text),
            sa.Column("content_format", TrimmedString(32)),
            sa.Column("edit_source", TrimmedString(16), default="user"),
        )

        # Add FK from notebook.latest_revision_id -> revision.id
        create_foreign_key(
            "history_notebook_latest_revision_id_fk",
            NOTEBOOK_TABLE,
            REVISION_TABLE,
            ["latest_revision_id"],
            ["id"],
        )

        # Page source provenance columns (Phase 7.1)
        add_column("page", sa.Column("source_invocation_id", sa.Integer, nullable=True))
        add_column("page", sa.Column("source_history_notebook_id", sa.Integer, nullable=True))

        create_index("ix_page_source_invocation_id", "page", ["source_invocation_id"])
        create_index("ix_page_source_history_notebook_id", "page", ["source_history_notebook_id"])

        create_foreign_key(
            "page_source_invocation_id_fkey",
            "page",
            "workflow_invocation",
            ["source_invocation_id"],
            ["id"],
        )
        create_foreign_key(
            "page_source_history_notebook_id_fkey",
            "page",
            "history_notebook",
            ["source_history_notebook_id"],
            ["id"],
        )


def downgrade():
    with transaction():
        # Drop page source provenance columns first (they FK to history_notebook)
        drop_constraint("page_source_history_notebook_id_fkey", "page")
        drop_constraint("page_source_invocation_id_fkey", "page")
        drop_index("ix_page_source_history_notebook_id", "page")
        drop_index("ix_page_source_invocation_id", "page")
        drop_column("page", "source_history_notebook_id")
        drop_column("page", "source_invocation_id")

        # Drop circular FK first, then revision table (has FK to notebook), then notebook
        drop_constraint("history_notebook_latest_revision_id_fk", NOTEBOOK_TABLE)
        drop_table(REVISION_TABLE)
        drop_table(NOTEBOOK_TABLE)
