"""add user defined object stores

Revision ID: c14a3c93d66a
Revises: 5924fbf10430
Create Date: 2023-04-01 17:25:37.553039

"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "c14a3c93d66a"
down_revision = "5924fbf10430"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "user_object_store"


def upgrade():
    create_table(
        table_name,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("galaxy_user.id"), nullable=False, index=True),
        Column("name", String(255), index=True),
        Column("description", Text, index=True),
        Column("create_time", DateTime),
        Column("update_time", DateTime),
        Column("object_store_template_id", String(255), index=True),
        Column("object_store_template_version", Integer, index=True),
        Column("object_store_template_definition", JSONType),
        Column("object_store_template_variables", JSONType),
        Column("object_store_template_secrets", JSONType),
    )


def downgrade():
    drop_table(table_name)
