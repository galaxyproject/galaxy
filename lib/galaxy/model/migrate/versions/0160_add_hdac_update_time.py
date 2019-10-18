"""
Adds create_time and update_time to hdac.
"""
import datetime
import logging

from sqlalchemy import Column, DateTime, MetaData, Table

from galaxy.model.migrate.versions.util import add_column, drop_column

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()
table_name = "history_dataset_collection_association"


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    create_time_column = Column("create_time", DateTime, default=now)
    update_time_column = Column("update_time", DateTime, default=now, onupdate=now)

    hdca_table = Table(table_name, metadata, autoload=True)
    add_column(create_time_column, hdca_table, metadata)
    add_column(update_time_column, hdca_table, metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    hdca_table = Table(table_name, metadata, autoload=True)
    drop_column("create_time", hdca_table)
    drop_column("update_time", hdca_table)
