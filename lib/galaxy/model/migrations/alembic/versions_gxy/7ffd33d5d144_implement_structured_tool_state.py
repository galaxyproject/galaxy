"""implement structured tool state

Revision ID: 7ffd33d5d144
Revises: c39f1de47a04
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

# revision identifiers, used by Alembic.
revision = "7ffd33d5d144"
down_revision = "c39f1de47a04"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tool_source",
        Column("id", Integer, primary_key=True),
        Column("hash", String(255), index=True),
        Column("source", JSONType),
    )
    op.create_table(
        "tool_request",
        Column("id", Integer, primary_key=True),
        Column("request", JSONType),
        Column("state", String(32)),
        Column("state_message", JSONType),
        Column("tool_source_id", Integer, ForeignKey("tool_sources.id"), index=True),
        Column("history_id", Integer, ForeignKey("history.id"), index=True),
    )
    op.add_column("job", Column("tool_request_id", Integer, ForeignKey("tool_source.id"), index=True))


def downgrade():
    op.drop_table("tool_request")
    op.drop_table("tool_source")
    op.drop_column("job", "tool_request_id")
