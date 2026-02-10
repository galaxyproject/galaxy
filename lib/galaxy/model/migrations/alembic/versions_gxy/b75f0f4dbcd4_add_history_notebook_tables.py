"""add history_notebook tables

Revision ID: b75f0f4dbcd4
Revises: 1d1d7bf6ac02, 23143e0bf1d8
Create Date: 2025-01-06

"""

import sqlalchemy as sa

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrations.util import (
    create_foreign_key,
    create_table,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "b75f0f4dbcd4"
down_revision = ("1d1d7bf6ac02", "23143e0bf1d8")
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


def downgrade():
    with transaction():
        drop_table(REVISION_TABLE)
        drop_table(NOTEBOOK_TABLE)
