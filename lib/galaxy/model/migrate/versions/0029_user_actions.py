"""
This migration script adds a user actions table to Galaxy.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, Unicode

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()


def display_migration_details():
    print("")
    print("This migration script adds a user actions table to Galaxy.")
    print("")


# New table to store user actions.
UserAction_table = Table( "user_action", metadata,
                          Column( "id", Integer, primary_key=True ),
                          Column( "create_time", DateTime, default=now ),
                          Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                          Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
                          Column( "action", Unicode( 255 ) ),
                          Column( "context", Unicode( 512 ) ),
                          Column( "params", Unicode( 1024 ) ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    display_migration_details()
    metadata.reflect()
    try:
        UserAction_table.create()
    except Exception as e:
        print(str(e))
        log.debug( "Creating user_action table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        UserAction_table.drop()
    except Exception as e:
        print(str(e))
        log.debug( "Dropping user_action table failed: %s" % str( e ) )
