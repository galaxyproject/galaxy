"""add export association table

Revision ID: 59e024ceaca1
Revises: e0e3bb173ee6
Create Date: 2022-10-12 18:02:34.659770

"""

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
)

from galaxy.model.custom_types import (
    JSONType,
    TrimmedString,
    UUIDType,
)
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "59e024ceaca1"
down_revision = "e0e3bb173ee6"
branch_labels = None
depends_on = None


table_name = "store_export_association"


def upgrade():
    create_table(
        table_name,
        Column("id", Integer, primary_key=True),
        Column("task_uuid", UUIDType(), index=True, unique=True),
        Column("create_time", DateTime),
        Column("object_type", TrimmedString(32)),
        Column("object_id", Integer),
        Column("export_metadata", JSONType),
    )


def downgrade():
    drop_table(table_name)
