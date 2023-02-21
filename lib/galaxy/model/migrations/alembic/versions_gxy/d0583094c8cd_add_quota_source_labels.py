"""add quota source labels

Revision ID: d0583094c8cd
Revises: c39f1de47a04
Create Date: 2022-06-09 12:24:44.329038

"""
from alembic import op
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
)

from galaxy.model.migrations.util import (
    add_unique_constraint,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "d0583094c8cd"
down_revision = "c39f1de47a04"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("quota", Column("quota_source_label", String(32), default=None))

    op.create_table(
        "user_quota_source_usage",
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
        Column("quota_source_label", String(32), index=True),
        # user had an index on disk_usage - does that make any sense? -John
        Column("disk_usage", Numeric(15, 0)),
    )
    add_unique_constraint("uqsu_unique_label_per_user", "user_quota_source_usage", ["user_id", "quota_source_label"])
    op.drop_index("ix_default_quota_association_type", "default_quota_association")
    op.create_index("ix_quota_quota_source_label", "quota", ["quota_source_label"])


def downgrade():
    op.create_index("ix_default_quota_association_type", "default_quota_association", ["type"], unique=True)
    op.drop_table("user_quota_source_usage")
    op.drop_index("ix_quota_quota_source_label", "quota")
    drop_column("quota", "quota_source_label")
