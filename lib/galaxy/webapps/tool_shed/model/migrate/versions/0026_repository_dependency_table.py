"""
Migration script to add the repository_dependency table.
"""
import datetime
import logging
import sys

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

now = datetime.datetime.utcnow

metadata = MetaData()

RepositoryDependency_table = Table( "repository_dependency", metadata,
                                    Column( "id", Integer, primary_key=True ),
                                    Column( "parent_metadata_id", Integer, ForeignKey( "repository_metadata.id" ), index=True ),
                                    Column( "required_metadata_id", Integer, ForeignKey( "repository_metadata.id" ), index=True ) )


def upgrade( migrate_engine ):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()
    # Create repository_dependency table.
    try:
        RepositoryDependency_table.create()
    except Exception, e:
        print "Creating the repository_dependency table failed: %s" % str( e )


def downgrade( migrate_engine ):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop the repository_dependency table.
    try:
        RepositoryDependency_table.drop()
    except Exception, e:
        print "Dropping the repository_dependency table failed: %s" % str( e )
