"""ensure dataset storage operation byte counters are bigint

Repair migration for dev-tracking databases that applied 28885b317f78
before fac9c76612f9 was re-parented beneath it (the release_26.1 forward
merge left two gxy heads; linearizing made fac9c76612f9 an ancestor of
28885b317f78, so alembic considers it applied on those databases and
never runs its bigint widening). Widens the columns only if they are
still INTEGER; a no-op everywhere else.

Downgrade is intentionally a no-op: the widening belongs to
fac9c76612f9, whose own downgrade narrows the columns back.

Revision ID: fb8621b7c075
Revises: 28885b317f78
Create Date: 2026-07-06 17:37:19.074881

"""

import logging

import sqlalchemy as sa
from alembic import (
    context,
    op,
)

from galaxy.model.migrations.util import alter_column

# revision identifiers, used by Alembic.
revision = "fb8621b7c075"
down_revision = "28885b317f78"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)

columns = [
    ("dataset_storage_operation_run", "total_bytes_processed"),
    ("dataset_storage_operation_run_item", "bytes_processed"),
]


def upgrade():
    for table_name, column_name in columns:
        if _needs_widening(table_name, column_name):
            alter_column(
                table_name,
                column_name,
                existing_type=sa.INTEGER(),
                type_=sa.BIGINT(),
                existing_nullable=False,
            )


def downgrade():
    pass


def _needs_widening(table_name: str, column_name: str) -> bool:
    if context.is_offline_mode():
        log.info(
            f"This script is being executed in offline mode, so it cannot inspect the type of "
            f"{table_name}.{column_name}. Assuming it is already BIGINT, which is the expected "
            f"state during normal operation."
        )
        return False
    bind = op.get_context().bind
    assert bind is not None  # not offline mode, so a connection exists
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return not isinstance(column["type"], sa.BigInteger)
    return False
