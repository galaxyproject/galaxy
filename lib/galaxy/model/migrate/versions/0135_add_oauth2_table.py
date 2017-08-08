"""
Migration script to add a new table named `galaxy_user_oauth2` for authentication and authorization.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT

log = logging.getLogger( __name__ )
metadata = MetaData()

UserOAuth2Table = Table(
    "galaxy_user_oauth2", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=False, index=True ),
    Column( "provider", TEXT, nullable=False ),
    Column( "state_token", TEXT, nullable=False, index=True ),
    Column( "id_token", TEXT, nullable=False ),
    Column( "refresh_token", TEXT, nullable=False ),
    Column( "expiration_date", DateTime, nullable=False ),
    Column( "access_token", TEXT ) )


def upgrade( migrate_engine ):
    print( __doc__ )
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create UserOAuth2Table
    try:
        UserOAuth2Table.create()
    except Exception as e:
        log.exception( "Creating UserOAuth2 table failed: %s" % str( e ) )


def downgrade( migrate_engine ):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop UserOAuth2Table
    try:
        UserOAuth2Table.drop()
    except Exception as e:
        log.exception( "Dropping UserOAuth2 table failed: %s" % str( e ) )
