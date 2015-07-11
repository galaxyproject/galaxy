"""
Migration script for the password reset table
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

PasswordResetToken_table = Table("password_reset_token", metadata,
                                 Column( "token", String( 32 ), primary_key=True, unique=True, index=True ),
                                 Column( "expiration_time", DateTime ),
                                 Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    try:
        PasswordResetToken_table.create()
    except Exception as e:
        print str(e)
        log.exception("Creating %s table failed: %s" % (PasswordResetToken_table.name, str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        PasswordResetToken_table.drop()
    except Exception as e:
        print str(e)
        log.exception("Dropping %s table failed: %s" % (PasswordResetToken_table.name, str( e ) ) )
