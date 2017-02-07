"""
Migration script to allow invalidation of job external output metadata temp files
"""
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, MetaData, Table

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    isvalid_column = Column( "is_valid", Boolean, default=True )
    __add_column( isvalid_column, "job_external_output_metadata", metadata )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        __drop_column( "is_valid", "job_external_output_metadata", metadata )


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table( table_name, metadata, autoload=True )
        column.create( table, **kwds )
    except Exception:
        log.exception("Adding column %s failed." % column)


def __drop_column( column_name, table_name, metadata ):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).drop()
    except Exception:
        log.exception("Dropping column %s failed." % column_name)
