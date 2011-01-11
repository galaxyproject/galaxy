"""
Migration script to add 'info' column to the transfer_job table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        TransferJob_table = Table( "transfer_job", metadata, autoload=True )
        c = Column( "info", TEXT )
        c.create( TransferJob_table )
        assert c is TransferJob_table.c.info
    except Exception, e:
        print "Adding info column to transfer_job table failed: %s" % str( e )
        log.debug( "Adding info column to transfer_job table failed: %s" % str( e ) )

def downgrade():
    metadata.reflect()
    try:
        TransferJob_table = Table( "transfer_job", metadata, autoload=True )
        TransferJob_table.c.info.drop()
    except Exception, e:
        print "Dropping info column from transfer_job table failed: %s" % str( e )
        log.debug( "Dropping info column from transfer_job table failed: %s" % str( e ) )
