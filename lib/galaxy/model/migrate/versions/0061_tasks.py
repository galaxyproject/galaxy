"""
Migration script to create tables task management.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
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

Task_table = Table("task", metadata,
                   Column("id", Integer, primary_key=True),
                   Column("create_time", DateTime, default=now),
                   Column("execution_time", DateTime),
                   Column("update_time", DateTime, default=now, onupdate=now),
                   Column("state", String(64), index=True),
                   Column("command_line", TEXT),
                   Column("param_filename", String(1024)),
                   Column("runner_name", String(255)),
                   Column("stdout", TEXT),
                   Column("stderr", TEXT),
                   Column("traceback", TEXT),
                   Column("job_id", Integer, ForeignKey("job.id"), index=True, nullable=False),
                   Column("part_file", String(1024)),
                   Column("task_runner_name", String(255)),
                   Column("task_runner_external_id", String(255)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(Task_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(Task_table)
