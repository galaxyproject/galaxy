"""
Migration script to add the long_description and times_downloaded columns to the repository table.
"""
import logging
import sys

from sqlalchemy import Column, Integer, MetaData, Table, TEXT

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def upgrade(migrate_engine):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()
    # Create and initialize imported column in job table.
    Repository_table = Table( "repository", metadata, autoload=True )
    c = Column( "long_description", TEXT )
    try:
        # Create
        c.create( Repository_table )
        assert c is Repository_table.c.long_description
    except Exception as e:
        print "Adding long_description column to the repository table failed: %s" % str( e )
        log.debug( "Adding long_description column to the repository table failed: %s" % str( e ) )

    c = Column( "times_downloaded", Integer )
    try:
        # Create
        c.create( Repository_table )
        assert c is Repository_table.c.times_downloaded
    except Exception as e:
        print "Adding times_downloaded column to the repository table failed: %s" % str( e )
        log.debug( "Adding times_downloaded column to the repository table failed: %s" % str( e ) )

    cmd = "UPDATE repository SET long_description = ''"
    migrate_engine.execute( cmd )
    cmd = "UPDATE repository SET times_downloaded = 0"
    migrate_engine.execute( cmd )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop email_alerts column from repository table.
    Repository_table = Table( "repository", metadata, autoload=True )
    try:
        Repository_table.c.long_description.drop()
    except Exception as e:
        print "Dropping column long_description from the repository table failed: %s" % str( e )
        log.debug( "Dropping column long_description from the repository table failed: %s" % str( e ) )
    try:
        Repository_table.c.times_downloaded.drop()
    except Exception as e:
        print "Dropping column times_downloaded from the repository table failed: %s" % str( e )
        log.debug( "Dropping column times_downloaded from the repository table failed: %s" % str( e ) )
