"""
Migration script to add a 'job_options' column to the
'workflow_request_input_parameter' table.
"""
from __future__ import print_function

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import JSONType

import logging

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    JobOptions_column = Column("job_options", JSONType)
    __add_column(JobOptions_column, "workflow_request_input_parameters", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column("job_options", "workflow_request_input_parameters", metadata)


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table(table_name, metadata, autoload=True)
        column.create(table, **kwds)
    except Exception:
        log.exception("Adding column %s column failed.", column)


def __drop_column(column_name, table_name, metadata):
    try:
        table = Table(table_name, metadata, autoload=True)
        getattr(table.c, column_name).drop()
    except Exception:
        log.exception("Dropping column %s failed.", column_name)
