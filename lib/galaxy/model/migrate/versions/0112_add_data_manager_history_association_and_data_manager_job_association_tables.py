"""
Migration script to add the data_manager_history_association table and data_manager_job_association.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    TEXT
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

DataManagerHistoryAssociation_table = Table("data_manager_history_association", metadata,
                                            Column("id", Integer, primary_key=True),
                                            Column("create_time", DateTime, default=now),
                                            Column("update_time", DateTime, index=True, default=now, onupdate=now),
                                            Column("history_id", Integer, ForeignKey("history.id"), index=True),
                                            Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True))

DataManagerJobAssociation_table = Table(
    "data_manager_job_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, index=True, default=now, onupdate=now),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("data_manager_id", TEXT),
    Index('ix_data_manager_job_association_data_manager_id', 'data_manager_id', mysql_length=200),
)

TABLES = [DataManagerHistoryAssociation_table, DataManagerJobAssociation_table]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        create_table(table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        drop_table(table)
