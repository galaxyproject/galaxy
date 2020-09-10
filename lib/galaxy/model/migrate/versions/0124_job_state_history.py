"""
Migration script for the job state history table
"""

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import create_table, drop_table

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

JobStateHistory_table = Table("job_state_history", metadata,
                              Column("id", Integer, primary_key=True),
                              Column("create_time", DateTime, default=now),
                              Column("update_time", DateTime, default=now, onupdate=now),
                              Column("job_id", Integer, ForeignKey("job.id"), index=True),
                              Column("state", String(64), index=True),
                              Column("info", TrimmedString(255)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(JobStateHistory_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(JobStateHistory_table)
