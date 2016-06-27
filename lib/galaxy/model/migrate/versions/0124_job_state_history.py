"""
Migration script for the job state history table
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table

from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()

JobStateHistory_table = Table( "job_state_history", metadata,
                               Column( "id", Integer, primary_key=True ),
                               Column( "create_time", DateTime, default=now ),
                               Column( "update_time", DateTime, default=now, onupdate=now ),
                               Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
                               Column( "state", String( 64 ), index=True ),
                               Column( "info", TrimmedString( 255 ) ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    try:
        JobStateHistory_table.create()
    except Exception as e:
        print(str(e))
        log.exception("Creating %s table failed: %s" % (JobStateHistory_table.name, str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        JobStateHistory_table.drop()
    except Exception as e:
        print(str(e))
        log.exception("Dropping %s table failed: %s" % (JobStateHistory_table.name, str( e ) ) )
