"""
Migration script to add 'purged' column to the library_dataset table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def boolean_false():
   if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
       return False
   elif migrate_engine.name == 'sqlite':
       return 0
   else:
       raise Exception( 'Unable to set True data value for unknown database type: %s' % str( migrate_engine.name ) )

def boolean_true():
   if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
       return True
   elif migrate_engine.name == 'sqlite':
       return 1
   else:
       raise Exception( 'Unable to set False data value for unknown database type: %s' % str( migrate_engine.name ) )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        LibraryDataset_table = Table( "library_dataset", metadata, autoload=True )
        c = Column( "purged", Boolean, index=True, default=False )
        c.create( LibraryDataset_table )
        assert c is LibraryDataset_table.c.purged
    except Exception, e:
        print "Adding purged column to library_dataset table failed: ", str( e )
    # Update the purged flag to the default False
    cmd = "UPDATE library_dataset SET purged = %s;" % boolean_false()
    try:
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Setting default data for library_dataset.purged column failed: %s" % ( str( e ) ) )

    # Update the purged flag for those LibaryDatasets whose purged flag should be True.  This happens
    # when the LibraryDataset has no active LibraryDatasetDatasetAssociations.
    cmd = "SELECT * FROM library_dataset WHERE deleted = %s;" % boolean_true()
    deleted_lds = db_session.execute( cmd ).fetchall()
    for row in deleted_lds:
        cmd = "SELECT * FROM library_dataset_dataset_association WHERE library_dataset_id = %d AND library_dataset_dataset_association.deleted = %s;" % ( int( row.id ), boolean_false() ) 
        active_lddas = db_session.execute( cmd ).fetchall()
        if not active_lddas:
            print "Updating purged column to True for LibraryDataset id : ", int( row.id )
            cmd = "UPDATE library_dataset SET purged = %s WHERE id = %d;" % ( boolean_true(), int( row.id ) )
            db_session.execute( cmd )

def downgrade():
    metadata.reflect()
    try:
        LibraryDataset_table = Table( "library_dataset", metadata, autoload=True )
        LibraryDataset_table.c.purged.drop()
    except Exception, e:
        print "Dropping purged column from library_dataset table failed: ", str( e )
