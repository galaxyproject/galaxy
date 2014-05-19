"""
Migration script for job metric plugins.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

TEXT_METRIC_MAX_LENGTH = 1023

JobMetricText_table = Table(
    "job_metric_text",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "plugin", Unicode(255), ),
    Column( "metric_name", Unicode(255), ),
    Column( "metric_value", Unicode(TEXT_METRIC_MAX_LENGTH), ),
)


TaskMetricText_table = Table(
    "task_metric_text",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "task_id", Integer, ForeignKey( "task.id" ), index=True ),
    Column( "plugin", Unicode(255), ),
    Column( "metric_name", Unicode(255), ),
    Column( "metric_value", Unicode(TEXT_METRIC_MAX_LENGTH), ),
)


JobMetricNumeric_table = Table(
    "job_metric_numeric",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "plugin", Unicode(255), ),
    Column( "metric_name", Unicode(255), ),
    Column( "metric_value", Numeric( 22, 7 ), ),
)


TaskMetricNumeric_table = Table(
    "task_metric_numeric",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "task_id", Integer, ForeignKey( "task.id" ), index=True ),
    Column( "plugin", Unicode(255), ),
    Column( "metric_name", Unicode(255), ),
    Column( "metric_value", Numeric( 22, 7 ), ),
)


TABLES = [
    JobMetricText_table,
    TaskMetricText_table,
    JobMetricNumeric_table,
    TaskMetricNumeric_table,
]


def upgrade( migrate_engine ):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    for table in TABLES:
        __create(table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        __drop(table)


def __create(table):
    try:
        table.create()
    except Exception as e:
        print str(e)
        log.debug("Creating %s table failed: %s" % (table.name, str( e ) ) )


def __drop(table):
    try:
        table.drop()
    except Exception as e:
        print str(e)
        log.debug("Dropping %s table failed: %s" % (table.name, str( e ) ) )
