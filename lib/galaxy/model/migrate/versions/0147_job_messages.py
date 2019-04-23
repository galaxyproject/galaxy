"""
Add structured failure reason column to jobs table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table, TEXT

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    add_column,
    alter_column,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    jobs_table = Table("job", metadata, autoload=True)
    job_messages_column = Column("job_messages", JSONType, nullable=True)
    add_column(job_messages_column, jobs_table)
    job_job_stdout_column = Column("job_stdout", TEXT, nullable=True)
    add_column(job_job_stdout_column, jobs_table)
    job_job_stderr_column = Column("job_stderr", TEXT, nullable=True)
    add_column(job_job_stderr_column, jobs_table)

    tasks_table = Table("task", metadata, autoload=True)
    task_job_messages_column = Column("job_messages", JSONType, nullable=True)
    add_column(task_job_messages_column, tasks_table)
    task_job_stdout_column = Column("job_stdout", TEXT, nullable=True)
    add_column(task_job_stdout_column, tasks_table)
    task_job_stderr_column = Column("job_stderr", TEXT, nullable=True)
    add_column(task_job_stderr_column, tasks_table)

    for table in [jobs_table, tasks_table]:
        alter_column('stdout', table, name='tool_stdout')
        alter_column('stderr', table, name='tool_stderr')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    jobs_table = Table("job", metadata, autoload=True)
    tasks_table = Table("task", metadata, autoload=True)
    for colname in ["job_messages", "job_stdout", "job_stderr"]:
        drop_column(colname, jobs_table)
        drop_column(colname, tasks_table)
    for table in [jobs_table, tasks_table]:
        alter_column('tool_stdout', table, name='stdout')
        alter_column('tool_stderr', table, name='stderr')
