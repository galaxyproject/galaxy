"""
This migration script changes certain values in the history_dataset_association.extension
column, specifically 'qual' is chaged to be 'qual454'.
"""
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

metadata = MetaData()

def display_migration_details():
    print "========================================"
    print "This migration script changes certain values in the history_dataset_association.extension"
    print "column, specifically 'qual' is chaged to be 'qual454'."
    print "========================================"


def upgrade(migrate_engine):
    display_migration_details()
    metadata.bind = migrate_engine
    db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )
    HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata, autoload=True )
    # Load existing tables
    metadata.reflect()
    # Add 2 indexes to the galaxy_user table
    i = Index( 'ix_hda_extension', HistoryDatasetAssociation_table.c.extension )
    try:
        i.create()
    except Exception, e:
        log.debug( "Adding index 'ix_hda_extension' to history_dataset_association table failed: %s" % ( str( e ) ) )

    # Set the default data in the galaxy_user table, but only for null values
    cmd = "UPDATE history_dataset_association SET extension = 'qual454' WHERE extension = 'qual' and peek like \'>%%\'"
    try:
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Resetting extension qual to qual454 in history_dataset_association failed: %s" % ( str( e ) ) )
    cmd = "UPDATE history_dataset_association SET extension = 'qualsolexa' WHERE extension = 'qual' and peek not like \'>%%\'"
    try:
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Resetting extension qual to qualsolexa in history_dataset_association failed: %s" % ( str( e ) ) )
    # Add 1 index to the history_dataset_association table
    try:
        i.drop()
    except Exception, e:
        log.debug( "Dropping index 'ix_hda_extension' to history_dataset_association table failed: %s" % ( str( e ) ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
