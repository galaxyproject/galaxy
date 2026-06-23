"""Remove unique constraint from role name, add not null constraint

Revision ID: 9a5207190a4d
Revises: a99a5b52ccb8
Create Date: 2024-10-08 14:08:28.418055

"""

import logging

from alembic import op
from sqlalchemy import text

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    alter_column,
    create_index,
    drop_index,
    transaction,
)

log = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "9a5207190a4d"
down_revision = "a99a5b52ccb8"
branch_labels = None
depends_on = None


table_name = "role"
column_name = "name"
index_name = build_index_name(table_name, [column_name])


def upgrade():
    with transaction():
        drop_index(index_name, table_name)
        alter_column(table_name, column_name, nullable=False)
        create_index(index_name, table_name, [column_name])


def downgrade():
    with transaction():
        alter_column(table_name, column_name, nullable=True)

        stmt = text("SELECT 1 FROM role GROUP BY name HAVING count(*) > 1")
        has_nonunique_values = op.get_bind().scalar(stmt)
        if not has_nonunique_values:
            drop_index(index_name, table_name)
            create_index(index_name, table_name, [column_name], unique=True)
        else:
            msg = f"""This downgrade requires creating a unique index on the `{table_name}.{column_name}` field.
This operation cannot proceed due to the existence of non-unique values in that column, which are the result of Galaxy v24.2 (and above)
operating under normal conditions. The current non-unique index will remain unchanged."""
            log.error(msg)
