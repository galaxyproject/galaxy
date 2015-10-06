"""
Expand the length of the password fields in the galaxy_user table to allow for other hasing schemes
"""
import logging

from sqlalchemy import MetaData, String, Table

log = logging.getLogger( __name__ )


def upgrade( migrate_engine ):
    meta = MetaData( bind=migrate_engine )
    user = Table( 'galaxy_user', meta, autoload=True )
    try:
        user.c.password.alter(type=String(255))
    except:
        log.exception( "Altering password column failed" )


def downgrade(migrate_engine):
    meta = MetaData( bind=migrate_engine )
    user = Table( 'galaxy_user', meta, autoload=True )
    try:
        user.c.password.alter(type=String(40))
    except:
        log.exception( "Altering password column failed" )
