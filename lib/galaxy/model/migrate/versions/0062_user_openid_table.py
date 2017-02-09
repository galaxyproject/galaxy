"""
Migration script to create table for associating sessions and users with
OpenIDs.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, MetaData, Table, TEXT

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()

# Table to add

UserOpenID_table = Table( "galaxy_user_openid", metadata,
                          Column( "id", Integer, primary_key=True ),
                          Column( "create_time", DateTime, default=now ),
                          Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
                          Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
                          Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                          Column( "openid", TEXT ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create galaxy_user_openid table
    try:
        UserOpenID_table.create()
    except Exception:
        log.exception("Creating galaxy_user_openid table failed.")

    ix_name = 'ix_galaxy_user_openid_openid'
    if migrate_engine.name == 'mysql':
        i = "ALTER TABLE galaxy_user_openid ADD UNIQUE INDEX ( openid( 255 ) )"
        migrate_engine.execute( i )
    else:
        i = Index( ix_name, UserOpenID_table.c.openid, unique=True )
        try:
            i.create()
        except Exception:
            log.exception("Adding index '%s' failed." % ix_name)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop galaxy_user_openid table
    try:
        UserOpenID_table.drop()
    except Exception:
        log.exception("Dropping galaxy_user_openid table failed.")
