"""
Migration script to allow invalidation of job external output metadata temp files
"""
import datetime
import logging

from sqlalchemy import Integer, Column, MetaData, Table
from galaxy.model.custom_types import JSONType

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    cwl_command_column = Column( "cwl_command_state", JSONType, default=True )
    cwl_command_version_column = Column( "cwl_command_state_version", Integer, default=True )
    __add_column( cwl_command_column, "job", metadata )
    __add_column( cwl_command_version_column, "job", metadata )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column( "cwl_command_state", "job", metadata )
    __drop_column( "cwl_command_state_version", "job", metadata )


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table( table_name, metadata, autoload=True )
        column.create( table, **kwds )
    except Exception as e:
        print str(e)
        log.exception( "Adding column %s failed." % column)


def __drop_column( column_name, table_name, metadata ):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).drop()
    except Exception as e:
        print str(e)
        log.exception( "Dropping column %s failed." % column_name )
