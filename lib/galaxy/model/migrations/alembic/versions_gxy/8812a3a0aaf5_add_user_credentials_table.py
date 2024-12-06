"""add user credentials table

Revision ID: 8812a3a0aaf5
Revises: 75348cfb3715
Create Date: 2024-12-04 15:15:02.919598

"""

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "8812a3a0aaf5"
down_revision = "75348cfb3715"
branch_labels = None
depends_on = None

table_name_1 = "user_credentials"
table_name_2 = "credentials"


def upgrade():
    create_table(
        table_name_1,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, index=True),
        Column("service_reference", TrimmedString(255)),
        Column("create_time", DateTime),
        Column("update_time", DateTime),
    )
    create_table(
        table_name_2,
        Column("id", Integer, primary_key=True),
        Column("user_credentials_id", Integer, index=True),
        Column("name", TrimmedString(255)),
        Column("type", TrimmedString(255)),
        Column("value", TrimmedString(255)),
        Column("create_time", DateTime),
        Column("update_time", DateTime),
    )


def downgrade():
    drop_table(table_name_1)
    drop_table(table_name_2)
