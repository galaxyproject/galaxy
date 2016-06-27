"""
Migration script to add 'prepare_input_files_cmd' column to the task table and to rename a column.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, String, Table, TEXT

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        task_table = Table( "task", metadata, autoload=True )
        c = Column( "prepare_input_files_cmd", TEXT, nullable=True )
        c.create( task_table )
        assert c is task_table.c.prepare_input_files_cmd
    except Exception as e:
        print("Adding prepare_input_files_cmd column to task table failed: %s" % str( e ))
        log.debug( "Adding prepare_input_files_cmd column to task table failed: %s" % str( e ) )
    try:
        task_table = Table( "task", metadata, autoload=True )
        c = Column( "working_directory", String( 1024 ), nullable=True )
        c.create( task_table )
        assert c is task_table.c.working_directory
    except Exception as e:
        print("Adding working_directory column to task table failed: %s" % str( e ))
        log.debug( "Adding working_directory column to task table failed: %s" % str( e ) )

    # remove the 'part_file' column - nobody used tasks before this, so no data needs to be migrated
    try:
        task_table.c.part_file.drop()
    except Exception as e:
        log.debug( "Deleting column 'part_file' from the 'task' table failed: %s" % ( str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        task_table = Table( "task", metadata, autoload=True )
        task_table.c.prepare_input_files_cmd.drop()
    except Exception as e:
        print("Dropping prepare_input_files_cmd column from task table failed: %s" % str( e ))
        log.debug( "Dropping prepare_input_files_cmd column from task table failed: %s" % str( e ) )
    try:
        task_table = Table( "task", metadata, autoload=True )
        task_table.c.working_directory.drop()
    except Exception as e:
        print("Dropping working_directory column from task table failed: %s" % str( e ))
        log.debug( "Dropping working_directory column from task table failed: %s" % str( e ) )
    try:
        task_table = Table( "task", metadata, autoload=True )
        c = Column( "part_file", String( 1024 ), nullable=True )
        c.create( task_table )
        assert c is task_table.c.part_file
    except Exception as e:
        print("Adding part_file column to task table failed: %s" % str( e ))
        log.debug( "Adding part_file column to task table failed: %s" % str( e ) )
