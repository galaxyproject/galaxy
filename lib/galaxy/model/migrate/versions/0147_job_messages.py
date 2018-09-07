"""
Add structured failure reason column to jobs table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
job_messages_column = Column("job_messages", JSONType, nullable=True)
task_job_messages_column = Column("job_messages", JSONType, nullable=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        jobs_table = Table("job", metadata, autoload=True)
        job_messages_column.create(jobs_table)
        assert job_messages_column is jobs_table.c.job_messages
    except Exception:
        log.exception("Adding column 'job_messages' to job table failed.")

    try:
        tasks_table = Table("task", metadata, autoload=True)
        task_job_messages_column.create(tasks_table)
        assert task_job_messages_column is tasks_table.c.job_messages
    except Exception:
        log.exception("Adding column 'job_messages' to task table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        jobs_table = Table("job", metadata, autoload=True)
        job_messages = jobs_table.c.job_messages
        job_messages.drop()
    except Exception:
        log.exception("Dropping 'job_messages' column from job table failed.")
    try:
        tasks_table = Table("task", metadata, autoload=True)
        job_messages = tasks_table.c.job_messages
        job_messages.drop()
    except Exception:
        log.exception("Dropping 'job_messages' column from task table failed.")
