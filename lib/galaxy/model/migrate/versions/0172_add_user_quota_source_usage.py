"""
Migration script to add a new user_quota_source_usage table.
"""

import logging

from migrate.changeset.constraint import UniqueConstraint as MigrateUniqueContraint
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Numeric, String, Table, UniqueConstraint

from galaxy.model.migrate.versions.util import (
    add_column,
    add_index,
    drop_column,
    drop_index,
)

log = logging.getLogger(__name__)
metadata = MetaData()

user_quota_source_usage_table = Table(
    "user_quota_source_usage", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("quota_source_label", String(32), index=True),
    # user had an index on disk_usage - does that make any sense? -John
    Column("disk_usage", Numeric(15, 0)),
    UniqueConstraint('user_id', 'quota_source_label', name="uqsu_unique_label_per_user"),
)
# Column to add.
quota_source_label_col = Column("quota_source_label", String(32), default=None, nullable=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    add_column(quota_source_label_col, 'quota', metadata)

    try:
        user_quota_source_usage_table.create()
    except Exception:
        log.exception("Creating user_quota_source_usage_table table failed")

    try:
        table = Table("default_quota_association", metadata, autoload=True)
        MigrateUniqueContraint("type", table=table).drop()
    except Exception:
        log.exception("Dropping unique constraint on default_quota_association.type failed")

    add_index("ix_quota_quota_source_label", "quota", "quota_source_label", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        user_quota_source_usage_table.drop()
    except Exception:
        log.exception("Dropping user_quota_source_usage_table table failed")

    drop_index("ix_quota_quota_source_label", "quota", "quota_source_label", metadata)
    drop_column(quota_source_label_col, 'quota', metadata)
