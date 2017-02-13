"""
Migration script for the password reset table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table

log = logging.getLogger( __name__ )
metadata = MetaData()

PasswordResetToken_table = Table("password_reset_token", metadata,
                                 Column( "token", String( 32 ), primary_key=True, unique=True, index=True ),
                                 Column( "expiration_time", DateTime ),
                                 Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        PasswordResetToken_table.create()
    except Exception:
        log.exception("Creating %s table failed." % PasswordResetToken_table.name)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        PasswordResetToken_table.drop()
    except Exception:
        log.exception("Dropping %s table failed." % PasswordResetToken_table.name)
