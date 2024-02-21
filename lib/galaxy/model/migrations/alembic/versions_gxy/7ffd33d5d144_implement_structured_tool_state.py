"""implement structured tool state

Revision ID: 7ffd33d5d144
Revises: 8a19186a6ee7
Create Date: 2022-11-09 15:53:11.451185

"""

from alembic import op
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    create_table,
    drop_column,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "7ffd33d5d144"
down_revision = "8a19186a6ee7"
branch_labels = None
depends_on = None


def upgrade():
    with transaction():
        create_table(
            "tool_source",
            Column("id", Integer, primary_key=True),
            Column("hash", String(255), index=True),
            Column("source", JSONType),
        )
        create_table(
            "tool_request",
            Column("id", Integer, primary_key=True),
            Column("request", JSONType),
            Column("state", String(32)),
            Column("state_message", JSONType),
            Column("tool_source_id", Integer, ForeignKey("tool_source.id"), index=True),
            Column("history_id", Integer, ForeignKey("history.id"), index=True),
        )
        add_column("job", Column("tool_request_id", Integer, ForeignKey("tool_request.id"), index=True))


def downgrade():
    with transaction():
        drop_column("job", "tool_request_id")
        drop_table("tool_request")
        drop_table("tool_source")
