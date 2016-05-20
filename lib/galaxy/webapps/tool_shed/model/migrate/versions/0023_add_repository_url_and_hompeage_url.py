"""
Migration script to add the remote_repository_url and homepage_url
columns to the repository table.
"""
import logging
import sys

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import TrimmedString

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def upgrade( migrate_engine ):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()
    Repository_table = Table( "repository", metadata, autoload=True )
    c_remote = Column( "remote_repository_url", TrimmedString( 255 ) )
    c_homepage = Column( "homepage_url", TrimmedString( 255 ) )
    try:
        # Create
        c_remote.create( Repository_table )
        c_homepage.create( Repository_table )
        assert c_remote is Repository_table.c.remote_repository_url
        assert c_homepage is Repository_table.c.homepage_url
    except Exception as e:
        print "Adding remote_repository_url and homepage_url columns to the repository table failed: %s" % str( e )


def downgrade( migrate_engine ):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop type column from repository table.
    Repository_table = Table( "repository", metadata, autoload=True )
    try:
        Repository_table.c.remote_repository_url.drop()
        Repository_table.c.homepage_url.drop()
    except Exception as e:
        print "Dropping columns remote_repository_url and homepage_url from the repository table failed: %s" % str( e )
