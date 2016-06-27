'''
Created on Sep 10, 2013

@author: marten

Adds 'active' and 'activation_token' columns to the galaxy_user table.
'''
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, MetaData, Table

from galaxy.model.custom_types import TrimmedString

log = logging.getLogger( __name__ )
user_active_column = Column( "active", Boolean, default=True, nullable=True )
user_activation_token_column = Column( "activation_token", TrimmedString( 64 ), nullable=True )


def display_migration_details():
    print("")
    print("This migration script adds active and activation_token columns to the user table")


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the active and activation_token columns to the user table in one try because the depend on each other.
    try:
        user_table = Table( "galaxy_user", metadata, autoload=True )
        user_active_column.create( table=user_table, populate_default=True)
        user_activation_token_column.create( table=user_table )
        assert user_active_column is user_table.c.active
        assert user_activation_token_column is user_table.c.activation_token
    except Exception as e:
        print(str(e))
        log.error( "Adding columns 'active' and 'activation_token' to galaxy_user table failed: %s" % str( e ) )
        return


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the user table's active and activation_token columns in one try because the depend on each other.
    try:
        user_table = Table( "galaxy_user", metadata, autoload=True )
        user_active = user_table.c.active
        user_activation_token = user_table.c.activation_token
        user_active.drop()
        user_activation_token.drop()
    except Exception as e:
        log.debug( "Dropping 'active' and 'activation_token' columns from galaxy_user table failed: %s" % ( str( e ) ) )
