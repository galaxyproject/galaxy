"""add quota source labels

Revision ID: d0583094c8cd
Revises: c39f1de47a04
Create Date: 2022-06-09 12:24:44.329038

"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
)

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    add_column,
    create_index,
    create_table,
    create_unique_constraint,
    drop_column,
    drop_constraint,
    drop_index,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "d0583094c8cd"
down_revision = "c39f1de47a04"
branch_labels = None
depends_on = None

old_index_name = build_index_name("default_quota_association", "type")
new_index_name = build_index_name("quota", "quota_source_label")
unique_constraint_name = "uqsu_unique_label_per_user"  # leave unchanged


def upgrade():
    with transaction():
        add_column("quota", Column("quota_source_label", String(32), default=None))
        create_table(
            "user_quota_source_usage",
            Column("id", Integer, primary_key=True),
            Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
            Column("quota_source_label", String(32), index=True),
            # user had an index on disk_usage - does that make any sense? -John
            Column("disk_usage", Numeric(15, 0)),
        )
        create_unique_constraint(unique_constraint_name, "user_quota_source_usage", ["user_id", "quota_source_label"])
        drop_index(old_index_name, "default_quota_association")
        create_index(new_index_name, "quota", ["quota_source_label"])


def downgrade():
    with transaction():
        drop_index(new_index_name, "quota")
        create_index(old_index_name, "default_quota_association", ["type"], unique=True)
        drop_constraint(unique_constraint_name, "user_quota_source_usage")
        drop_table("user_quota_source_usage")
        drop_column("quota", "quota_source_label")
