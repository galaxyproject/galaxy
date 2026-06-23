"""add user defined file sources

Revision ID: c14a3c93d66b
Revises: c14a3c93d66a
Create Date: 2023-04-01 17:25:37.553039

"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from galaxy.model.custom_types import (
    JSONType,
    UUIDType,
)
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "c14a3c93d66b"
down_revision = "c14a3c93d66a"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "user_file_source"


def upgrade():
    create_table(
        table_name,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("galaxy_user.id"), nullable=False, index=True),
        Column("uuid", UUIDType, nullable=False, index=True),
        Column("name", String(255), index=True),
        Column("description", Text, index=True),
        Column("hidden", Boolean, default=False, nullable=False),
        Column("active", Boolean, default=True, nullable=False),
        Column("purged", Boolean, default=False, nullable=False),
        Column("create_time", DateTime),
        Column("update_time", DateTime),
        Column("template_id", String(255), index=True),
        Column("template_version", Integer, index=True),
        Column("template_definition", JSONType),
        Column("template_variables", JSONType),
        Column("template_secrets", JSONType),
    )


def downgrade():
    drop_table(table_name)
