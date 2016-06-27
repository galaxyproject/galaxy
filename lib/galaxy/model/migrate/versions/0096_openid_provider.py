"""
Migration script to add column to openid table for provider.
Remove any OpenID entries with nonunique GenomeSpace Identifier
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import TrimmedString

log = logging.getLogger( __name__ )
BAD_IDENTIFIER = 'https://identity.genomespace.org/identityServer/xrd.jsp'
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    try:
        OpenID_table = Table( "galaxy_user_openid", metadata, autoload=True )
        c = Column( "provider", TrimmedString( 255 ) )
        c.create( OpenID_table )
        assert c is OpenID_table.c.provider
    except Exception as e:
        print("Adding provider column to galaxy_user_openid table failed: %s" % str( e ))
        log.debug( "Adding provider column to galaxy_user_openid table failed: %s" % str( e ) )

    try:
        cmd = "DELETE FROM galaxy_user_openid WHERE openid='%s'" % ( BAD_IDENTIFIER )
        migrate_engine.execute( cmd )
    except Exception as e:
        log.debug( "Deleting bad Identifiers from galaxy_user_openid failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        OpenID_table = Table( "galaxy_user_openid", metadata, autoload=True )
        OpenID_table.c.provider.drop()
    except Exception as e:
        print("Dropping provider column from galaxy_user_openid table failed: %s" % str( e ))
        log.debug( "Dropping provider column from galaxy_user_openid table failed: %s" % str( e ) )
