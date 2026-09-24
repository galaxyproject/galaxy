"""increase dataset_storage_operation_run total_bytes_processed to bigint

Revision ID: fac9c76612f9
Revises: 6925fe4c8a17
Create Date: 2026-06-27 09:42:18.664714

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import alter_column

# revision identifiers, used by Alembic.
revision = "fac9c76612f9"
down_revision = "6925fe4c8a17"
branch_labels = None
depends_on = None

run_table_name = "dataset_storage_operation_run"
run_total_bytes_column = "total_bytes_processed"

item_table_name = "dataset_storage_operation_run_item"
item_bytes_column = "bytes_processed"


def upgrade():
    alter_column(
        run_table_name,
        run_total_bytes_column,
        existing_type=sa.INTEGER(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )
    alter_column(
        item_table_name,
        item_bytes_column,
        existing_type=sa.INTEGER(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )


def downgrade():
    alter_column(
        run_table_name,
        run_total_bytes_column,
        existing_type=sa.BIGINT(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
    alter_column(
        item_table_name,
        item_bytes_column,
        existing_type=sa.BIGINT(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
