"""add archived columns to history

Revision ID: e0561d5fc8c7
Revises: 2d749563e1fe
Create Date: 2023-05-03 11:57:58.710098

"""

import sqlalchemy as sa

from galaxy.model.database_object_names import (
    build_foreign_key_name,
    build_index_name,
)
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
revision = "e0561d5fc8c7"
down_revision = "2d749563e1fe"
branch_labels = None
depends_on = None

table_name = "history"

archived_column_name = "archived"
archived_column_index_name = build_index_name(table_name, archived_column_name)

ref_table_name = "store_export_association"
archived_export_id_column_name = "archive_export_id"
archived_export_id_column_fk_name = build_foreign_key_name(table_name, archived_export_id_column_name)


def upgrade():
    with transaction():
        _add_column_archived()
        _add_column_archive_export_id()


def downgrade():
    with transaction():
        _drop_column_archived()
        _drop_column_archive_export_id()


def _add_column_archived():
    add_column(
        table_name,
        sa.Column(archived_column_name, sa.Boolean(), default=False, server_default=sa.false()),
    )
    create_index(archived_column_index_name, table_name, [archived_column_name])


def _add_column_archive_export_id():
    add_column(
        table_name,
        sa.Column(archived_export_id_column_name, sa.Integer, nullable=True, default=None),
    )
    create_foreign_key(
        archived_export_id_column_fk_name, table_name, ref_table_name, [archived_export_id_column_name], ["id"]
    )


def _drop_column_archived():
    drop_index(archived_column_index_name, table_name)
    drop_column(table_name, archived_column_name)


def _drop_column_archive_export_id():
    drop_constraint(archived_export_id_column_fk_name, table_name)
    drop_column(table_name, archived_export_id_column_name)
