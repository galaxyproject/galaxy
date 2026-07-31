"""add project folder for grouping histories

Adds an optional, flat, per-user grouping for a user's own histories.

The history column is nullable with no default, so every existing history
starts out unfiled and nothing about the current behaviour changes until a
user creates a folder. Dropping a folder releases its histories rather than
deleting them, hence ON DELETE SET NULL.

Revision ID: a1f3c27d9b04
Revises: fb8621b7c075
Create Date: 2026-07-31 09:05:00.000000

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
revision = "a1f3c27d9b04"
down_revision = "fb8621b7c075"
branch_labels = None
depends_on = None

table_name = "project_folder"
history_table_name = "history"
history_column_name = "project_folder_id"
history_column_index_name = "ix_history_project_folder_id"
history_column_fk_name = "history_project_folder_id_fkey"


def upgrade():
    with transaction():
        create_table(
            table_name,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("create_time", sa.DateTime),
            sa.Column("update_time", sa.DateTime),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True, nullable=False),
            sa.Column("name", TrimmedString(255), nullable=False),
            sa.UniqueConstraint("user_id", "name", name="unique_project_folder_name_per_user"),
        )
        # The column and its constraint are added separately: SQLite cannot
        # ALTER a foreign key into an existing table, so inlining it here would
        # break the migration on SQLite installs.
        add_column(
            history_table_name,
            sa.Column(history_column_name, sa.Integer, nullable=True, default=None),
        )
        create_index(history_column_index_name, history_table_name, [history_column_name])
        create_foreign_key(
            history_column_fk_name,
            history_table_name,
            table_name,
            [history_column_name],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with transaction():
        # Dropping the column discards which folder each history was filed
        # under. The histories themselves are untouched, so this loses only the
        # grouping.
        drop_constraint(history_column_fk_name, history_table_name)
        drop_index(history_column_index_name, history_table_name)
        drop_column(history_table_name, history_column_name)
        drop_table(table_name)
