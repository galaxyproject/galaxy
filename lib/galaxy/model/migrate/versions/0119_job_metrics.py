"""
Migration script for job metric plugins.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    Table,
    Unicode
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

TEXT_METRIC_MAX_LENGTH = 1023

JobMetricText_table = Table(
    "job_metric_text",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("plugin", Unicode(255), ),
    Column("metric_name", Unicode(255), ),
    Column("metric_value", Unicode(TEXT_METRIC_MAX_LENGTH), ),
)


TaskMetricText_table = Table(
    "task_metric_text",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("task_id", Integer, ForeignKey("task.id"), index=True),
    Column("plugin", Unicode(255), ),
    Column("metric_name", Unicode(255), ),
    Column("metric_value", Unicode(TEXT_METRIC_MAX_LENGTH), ),
)


JobMetricNumeric_table = Table(
    "job_metric_numeric",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("plugin", Unicode(255), ),
    Column("metric_name", Unicode(255), ),
    Column("metric_value", Numeric(22, 7), ),
)


TaskMetricNumeric_table = Table(
    "task_metric_numeric",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("task_id", Integer, ForeignKey("task.id"), index=True),
    Column("plugin", Unicode(255), ),
    Column("metric_name", Unicode(255), ),
    Column("metric_value", Numeric(22, 7), ),
)


TABLES = [
    JobMetricText_table,
    TaskMetricText_table,
    JobMetricNumeric_table,
    TaskMetricNumeric_table,
]


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
