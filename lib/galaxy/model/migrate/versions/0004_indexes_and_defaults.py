from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
import sys, logging

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )
User_table = Table( "galaxy_user", metadata, autoload=True )
HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata, autoload=True )

def boolean_false():
   if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
       return False
   elif migrate_engine.name == 'sqlite':
       return 0
   else:
       raise Exception( 'Unable to convert data for unknown database type: %s' % db )
              
def upgrade():
    # Load existing tables
    metadata.reflect()
    # Add 2 indexes to the galaxy_user table
    i = Index( 'ix_galaxy_user_deleted', User_table.c.deleted )
    try:
        i.create()
    except Exception, e:
        log.debug( "Adding index 'ix_galaxy_user_deleted' to galaxy_user table failed: %s" % ( str( e ) ) )
    i = Index( 'ix_galaxy_user_purged', User_table.c.purged )
    try:
        i.create()
    except Exception, e:
        log.debug( "Adding index 'ix_galaxy_user_purged' to galaxy_user table failed: %s" % ( str( e ) ) )
    # Set the default data in the galaxy_user table, but only for null values
    cmd = "UPDATE galaxy_user SET deleted = %s WHERE deleted is null"
    cmd = cmd % boolean_false()
    try:
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Setting default data for galaxy_user.deleted column failed: %s" % ( str( e ) ) )
    cmd = "UPDATE galaxy_user SET purged = %s WHERE purged is null"
    cmd = cmd % boolean_false()
    try:
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Setting default data for galaxy_user.purged column failed: %s" % ( str( e ) ) )
    # Add 1 index to the history_dataset_association table
    i = Index( 'ix_hda_copied_from_library_dataset_dataset_association_id', HistoryDatasetAssociation_table.c.copied_from_library_dataset_dataset_association_id )
    try:
        i.create()
    except Exception, e:
        log.debug( "Adding index 'ix_hda_copied_from_library_dataset_dataset_association_id' to history_dataset_association table failed: %s" % ( str( e ) ) )
def downgrade():
    pass
