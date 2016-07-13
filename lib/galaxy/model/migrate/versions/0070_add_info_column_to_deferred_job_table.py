"""
Migration script to add 'info' column to the transfer_job table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table, TEXT

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        TransferJob_table = Table( "transfer_job", metadata, autoload=True )
        c = Column( "info", TEXT )
        c.create( TransferJob_table )
        assert c is TransferJob_table.c.info
    except Exception as e:
        print("Adding info column to transfer_job table failed: %s" % str( e ))
        log.debug( "Adding info column to transfer_job table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        TransferJob_table = Table( "transfer_job", metadata, autoload=True )
        TransferJob_table.c.info.drop()
    except Exception as e:
        print("Dropping info column from transfer_job table failed: %s" % str( e ))
        log.debug( "Dropping info column from transfer_job table failed: %s" % str( e ) )
