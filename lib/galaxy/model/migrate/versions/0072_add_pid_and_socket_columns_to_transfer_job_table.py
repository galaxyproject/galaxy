"""
Migration script to add 'pid' and 'socket' columns to the transfer_job table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    try:
        TransferJob_table = Table( "transfer_job", metadata, autoload=True )
        c = Column( "pid", Integer )
        c.create( TransferJob_table )
        assert c is TransferJob_table.c.pid
        c = Column( "socket", Integer )
        c.create( TransferJob_table )
        assert c is TransferJob_table.c.socket
    except Exception, e:
        print "Adding columns to transfer_job table failed: %s" % str( e )
        log.debug( "Adding columns to transfer_job table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        TransferJob_table = Table( "transfer_job", metadata, autoload=True )
        TransferJob_table.c.pid.drop()
        TransferJob_table.c.socket.drop()
    except Exception, e:
        print "Dropping columns from transfer_job table failed: %s" % str( e )
        log.debug( "Dropping columns from transfer_job table failed: %s" % str( e ) )
