"""
Migration script to create tables task management.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table, TEXT

log = logging.getLogger( __name__ )
metadata = MetaData()
now = datetime.datetime.utcnow

Task_table = Table( "task", metadata,
                    Column( "id", Integer, primary_key=True ),
                    Column( "create_time", DateTime, default=now ),
                    Column( "execution_time", DateTime ),
                    Column( "update_time", DateTime, default=now, onupdate=now ),
                    Column( "state", String( 64 ), index=True ),
                    Column( "command_line", TEXT ),
                    Column( "param_filename", String( 1024 ) ),
                    Column( "runner_name", String( 255 ) ),
                    Column( "stdout", TEXT ),
                    Column( "stderr", TEXT ),
                    Column( "traceback", TEXT ),
                    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True, nullable=False ),
                    Column( "part_file", String(1024)),
                    Column( "task_runner_name", String( 255 ) ),
                    Column( "task_runner_external_id", String( 255 ) ) )

tables = [Task_table]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    for table in tables:
        try:
            table.create()
        except:
            log.warning( "Failed to create table '%s', ignoring (might result in wrong schema)" % table.name )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    for table in tables:
        table.drop()
