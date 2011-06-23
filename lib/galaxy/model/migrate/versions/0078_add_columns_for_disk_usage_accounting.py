"""
Migration script to add 'total_size' column to the dataset table, 'purged'
column to the HDA table, and 'disk_usage' column to the User and GalaxySession
tables.
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
        Dataset_table = Table( "dataset", metadata, autoload=True )
        c = Column( 'total_size', Numeric( 15, 0 ) )
        c.create( Dataset_table )
        assert c is Dataset_table.c.total_size
    except Exception, e:
        print "Adding total_size column to dataset table failed: %s" % str( e )
        log.debug( "Adding total_size column to dataset table failed: %s" % str( e ) )

    try:
        HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata, autoload=True )
        c = Column( "purged", Boolean, index=True, default=False )
        c.create( HistoryDatasetAssociation_table )
        assert c is HistoryDatasetAssociation_table.c.purged
        db_session.execute(HistoryDatasetAssociation_table.update().values(purged=False))
    except Exception, e:
        print "Adding purged column to history_dataset_association table failed: %s" % str( e )
        log.debug( "Adding purged column to history_dataset_association table failed: %s" % str( e ) )

    try:
        User_table = Table( "galaxy_user", metadata, autoload=True )
        c = Column( 'disk_usage', Numeric( 15, 0 ), index=True )
        c.create( User_table )
        assert c is User_table.c.disk_usage
    except Exception, e:
        print "Adding disk_usage column to galaxy_user table failed: %s" % str( e )
        log.debug( "Adding disk_usage column to galaxy_user table failed: %s" % str( e ) )

    try:
        GalaxySession_table = Table( "galaxy_session", metadata, autoload=True )
        c = Column( 'disk_usage', Numeric( 15, 0 ), index=True )
        c.create( GalaxySession_table )
        assert c is GalaxySession_table.c.disk_usage
    except Exception, e:
        print "Adding disk_usage column to galaxy_session table failed: %s" % str( e )
        log.debug( "Adding disk_usage column to galaxy_session table failed: %s" % str( e ) )

def downgrade():
    metadata.reflect()
    try:
        Dataset_table = Table( "dataset", metadata, autoload=True )
        Dataset_table.c.total_size.drop()
    except Exception, e:
        print "Dropping total_size column from dataset table failed: %s" % str( e )
        log.debug( "Dropping total_size column from dataset table failed: %s" % str( e ) )

    try:
        HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata, autoload=True )
        HistoryDatasetAssociation_table.c.purged.drop()
    except Exception, e:
        print "Dropping purged column from history_dataset_association table failed: %s" % str( e )
        log.debug( "Dropping purged column from history_dataset_association table failed: %s" % str( e ) )

    try:
        User_table = Table( "galaxy_user", metadata, autoload=True )
        User_table.c.disk_usage.drop()
    except Exception, e:
        print "Dropping disk_usage column from galaxy_user table failed: %s" % str( e )
        log.debug( "Dropping disk_usage column from galaxy_user table failed: %s" % str( e ) )

    try:
        GalaxySession_table = Table( "galaxy_session", metadata, autoload=True )
        GalaxySession_table.c.disk_usage.drop()
    except Exception, e:
        print "Dropping disk_usage column from galaxy_session table failed: %s" % str( e )
        log.debug( "Dropping disk_usage column from galaxy_session table failed: %s" % str( e ) )
