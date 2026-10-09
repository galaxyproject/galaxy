"""add user credentials table

Revision ID: c8c9bd29810d
Revises: e382f8eb5e12
Create Date: 2025-07-18 13:38:09.608283

"""

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
    add_column,
    create_foreign_key,
    create_table,
    create_unique_constraint,
    drop_constraint,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "c8c9bd29810d"
down_revision = "e382f8eb5e12"
branch_labels = None
depends_on = None


user_credentials_table = "user_credentials"
credentials_group_table = "credentials_group"
credential_table = "credential"
current_group_id_column_name = "current_group_id"
current_group_id_fk_name = build_foreign_key_name(user_credentials_table, current_group_id_column_name)
user_credentials_unique_constraint_name = "uq_user_credentials"


def upgrade():
    with transaction():
        create_table(
            user_credentials_table,
            Column("id", Integer, primary_key=True),
            Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
            Column("source_type", TrimmedString(255)),
            Column("source_id", TrimmedString(255)),
            Column("source_version", TrimmedString(255)),
            Column("name", TrimmedString(255)),
            Column("version", TrimmedString(255)),
            Column("create_time", DateTime),
            Column("update_time", DateTime),
        )
        create_unique_constraint(
            user_credentials_unique_constraint_name,
            user_credentials_table,
            ["user_id", "source_type", "source_id", "source_version", "name", "version"],
        )
        create_table(
            credentials_group_table,
            Column("id", Integer, primary_key=True),
            Column(
                "user_credentials_id",
                Integer,
                ForeignKey(f"{user_credentials_table}.id", ondelete="CASCADE"),
                index=True,
            ),
            Column("name", TrimmedString(255)),
            Column("create_time", DateTime),
            Column("update_time", DateTime),
        )
        add_column(user_credentials_table, Column(current_group_id_column_name, Integer, index=True, nullable=True))
        create_foreign_key(
            current_group_id_fk_name,
            user_credentials_table,
            credentials_group_table,
            [current_group_id_column_name],
            ["id"],
            ondelete="CASCADE",
        )
        create_table(
            credential_table,
            Column("id", Integer, primary_key=True),
            Column("group_id", Integer, ForeignKey(f"{credentials_group_table}.id", ondelete="CASCADE"), index=True),
            Column("name", TrimmedString(255)),
            Column("is_secret", Boolean),
            Column("is_set", Boolean),
            Column("value", TrimmedString(255), nullable=True),
            Column("create_time", DateTime),
            Column("update_time", DateTime),
        )


def downgrade():
    with transaction():
        drop_constraint(current_group_id_fk_name, user_credentials_table)

        drop_table(credential_table)
        drop_table(credentials_group_table)
        drop_table(user_credentials_table)
