"""
Add structured failure reason column to jobs table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table, TEXT

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
job_messages_column = Column("job_messages", JSONType, nullable=True)
task_job_messages_column = Column("job_messages", JSONType, nullable=True)
job_job_stdout_column = Column("job_stdout", TEXT, nullable=True)
job_job_stderr_column = Column("job_stderr", TEXT, nullable=True)
task_job_stdout_column = Column("job_stdout", TEXT, nullable=True)
task_job_stderr_column = Column("job_stderr", TEXT, nullable=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        jobs_table = Table("job", metadata, autoload=True)
        job_messages_column.create(jobs_table)
        assert job_messages_column is jobs_table.c.job_messages

        job_job_stdout_column.create(jobs_table)
        job_job_stderr_column.create(jobs_table)

        jobs_table.c.stdout.alter(name="tool_stdout")
        jobs_table.c.stderr.alter(name="tool_stderr")

        tasks_table = Table("task", metadata, autoload=True)
        task_job_messages_column.create(tasks_table)
        assert task_job_messages_column is tasks_table.c.job_messages

        task_job_stdout_column.create(tasks_table)
        task_job_stderr_column.create(tasks_table)

        tasks_table.c.stdout.alter(name="tool_stdout")
        tasks_table.c.stderr.alter(name="tool_stderr")
    except Exception:
        log.exception("Failed to alter jobs and/or tasks tables.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        jobs_table = Table("job", metadata, autoload=True)
        tasks_table = Table("task", metadata, autoload=True)

        for colname in ["job_messages", "job_stdout", "job_stderr"]:
            job_col = getattr(jobs_table.c, colname)
            job_col.drop()
            task_col = getattr(tasks_table.c, colname)
            task_col.drop()

        for table in [jobs_table, tasks_table]:
            table.c.tool_stdout.alter(name="stdout")
            table.c.tool_stderr.alter(name="stderr")

    except Exception:
        log.exception("Failed to alter jobs and/or tasks tables.")
