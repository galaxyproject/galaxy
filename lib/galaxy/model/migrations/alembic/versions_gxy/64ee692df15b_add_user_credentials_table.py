"""add user credentials table

Revision ID: 64ee692df15b
Revises: 75348cfb3715
Create Date: 2024-12-19 10:38:04.970502

"""

from alembic.op import batch_alter_table
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.database_object_names import build_foreign_key_name
from galaxy.model.migrations.util import (
    create_table,
    drop_constraint,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "64ee692df15b"
down_revision = "75348cfb3715"
branch_labels = None
depends_on = None


user_credentials_table = "user_credentials"
user_credentials_group_table = "user_credentials_group"
variable_table = "credential_variable"
secret_table = "credential_secret"


def upgrade():
    create_table(
        user_credentials_table,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True, nullable=False),
        Column("reference", TrimmedString(255), nullable=False),
        Column("source_type", TrimmedString(255), nullable=False),
        Column("source_id", TrimmedString(255), nullable=False),
        Column("create_time", DateTime),
        Column("update_time", DateTime),
    )
    create_table(
        user_credentials_group_table,
        Column("id", Integer, primary_key=True),
        Column("name", TrimmedString(255), nullable=False),
        Column("user_credentials_id", Integer, ForeignKey("user_credentials.id"), index=True, nullable=False),
        Column("create_time", DateTime),
        Column("update_time", DateTime),
    )
    with batch_alter_table(user_credentials_table) as batch_op:
        batch_op.add_column(
            Column("current_group_id", Integer, ForeignKey("user_credentials_group.id"), index=True, nullable=True)
        )
    create_table(
        variable_table,
        Column("id", Integer, primary_key=True),
        Column(
            "user_credential_group_id", Integer, ForeignKey("user_credentials_group.id"), index=True, nullable=False
        ),
        Column("name", TrimmedString(255), nullable=False),
        Column("value", TrimmedString(255), nullable=False),
        Column("create_time", DateTime),
        Column("update_time", DateTime),
    )
    create_table(
        secret_table,
        Column("id", Integer, primary_key=True),
        Column(
            "user_credential_group_id", Integer, ForeignKey("user_credentials_group.id"), index=True, nullable=False
        ),
        Column("name", TrimmedString(255), nullable=False),
        Column("already_set", Boolean, nullable=False),
        Column("create_time", DateTime),
        Column("update_time", DateTime),
    )


def downgrade():
    drop_constraint(build_foreign_key_name(user_credentials_table, "current_group_id"), user_credentials_table)

    drop_table(variable_table)
    drop_table(secret_table)
    drop_table(user_credentials_group_table)
    drop_table(user_credentials_table)
