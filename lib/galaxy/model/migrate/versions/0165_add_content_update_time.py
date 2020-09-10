"""
Adds timestamps to hdca table. Adds triggers to dataset, hda, hdca tables
to update history.update_time when contents are changed.
"""

import logging

from sqlalchemy import Column, DateTime, MetaData, Table

from galaxy.model.migrate.versions.util import add_column, drop_column
from galaxy.model.orm.now import now
from galaxy.model.triggers import drop_timestamp_triggers, install_timestamp_triggers

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    create_timestamps(metadata, "history_dataset_collection_association")
    install_timestamp_triggers(migrate_engine)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_timestamp_triggers(migrate_engine)
    drop_timestamps(metadata, "history_dataset_collection_association")


def create_timestamps(metadata, table_name):
    target_table = Table(table_name, metadata, autoload=True)
    if 'create_time' not in target_table.c:
        create_time_column = Column("create_time", DateTime, default=now)
        add_column(create_time_column, target_table, metadata)
    if 'update_time' not in target_table.c:
        update_time_column = Column("update_time", DateTime, default=now, onupdate=now)
        add_column(update_time_column, target_table, metadata)


def drop_timestamps(metadata, table_name):
    target_table = Table(table_name, metadata, autoload=True)
    drop_column("create_time", target_table)
    drop_column("update_time", target_table)
