"""Add GalaxyToolSourceAssociation table

Revision ID: 27044275d420
Revises: 1d1d7bf6ac02
Create Date: 2025-11-11 13:47:57.306214

"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrations.util import (
    add_column,
    create_table,
    drop_column,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "27044275d420"
down_revision = "1d1d7bf6ac02"
branch_labels = None
depends_on = None

galaxy_tool_source_association_table = "galaxy_tool_source_association"


def upgrade():
    with transaction():
        create_table(
            galaxy_tool_source_association_table,
            Column("id", Integer, primary_key=True),
            Column("tool_id", TrimmedString(255)),
            Column("tool_dir", TrimmedString(255)),
            Column("tool_source_id", Integer, ForeignKey("tool_source.id")),
        )
        add_column("tool_source", Column("tool_source_class", TrimmedString(255)))


def downgrade():
    with transaction():
        drop_table(galaxy_tool_source_association_table)
        drop_column("tool_source", "tool_source_class")
