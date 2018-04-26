"""
Migration script to add the job_metric_file and task_metric_file tables.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Unicode

log = logging.getLogger(__name__)
metadata = MetaData()


job_metric_file = Table(
    "job_metric_file", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("plugin", Unicode(255)),
    Column("metric_name", Unicode(255)),
    Column("metric_value", Unicode(255)),
    Column("object_store_id", Unicode(255)))


task_metric_file = Table(
    "task_metric_file", metadata,
    Column("id", Integer, primary_key=True),
    Column("task_id", Integer, ForeignKey("task.id"), index=True),
    Column("plugin", Unicode(255)),
    Column("metric_name", Unicode(255)),
    Column("metric_value", Unicode(255)),
    Column("object_store_id", Unicode(255)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        job_metric_file.create()
        task_metric_file.create()
    except Exception as e:
        log.exception("Creating metric file table failed: %s", str(e))


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        job_metric_file.drop()
        task_metric_file.drop()
    except Exception as e:
        log.exception("Dropping metric file table failed: %s", str(e))
