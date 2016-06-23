"""
Adds the repository, repository_rating_association and repository_category_association tables.
"""
import datetime
import logging
import sys

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

Repository_table = Table( "repository", metadata,
                          Column( "id", Integer, primary_key=True ),
                          Column( "create_time", DateTime, default=now ),
                          Column( "update_time", DateTime, default=now, onupdate=now ),
                          Column( "name", TrimmedString( 255 ), index=True ),
                          Column( "description", TEXT ),
                          Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                          Column( "private", Boolean, default=False ),
                          Column( "deleted", Boolean, index=True, default=False ) )

RepositoryRatingAssociation_table = Table( "repository_rating_association", metadata,
                                           Column( "id", Integer, primary_key=True ),
                                           Column( "create_time", DateTime, default=now ),
                                           Column( "update_time", DateTime, default=now, onupdate=now ),
                                           Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
                                           Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                                           Column( "rating", Integer, index=True ),
                                           Column( "comment", TEXT ) )

RepositoryCategoryAssociation_table = Table( "repository_category_association", metadata,
                                             Column( "id", Integer, primary_key=True ),
                                             Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
                                             Column( "category_id", Integer, ForeignKey( "category.id" ), index=True ) )


def upgrade(migrate_engine):
    print __doc__
    # Load existing tables
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        Repository_table.create()
    except Exception as e:
        log.debug( "Creating repository table failed: %s" % str( e ) )
    try:
        RepositoryRatingAssociation_table.create()
    except Exception as e:
        log.debug( "Creating repository_rating_association table failed: %s" % str( e ) )
    try:
        RepositoryCategoryAssociation_table.create()
    except Exception as e:
        log.debug( "Creating repository_category_association table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    # Load existing tables
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        Repository_table.drop()
    except Exception as e:
        log.debug( "Dropping repository table failed: %s" % str( e ) )
    try:
        RepositoryRatingAssociation_table.drop()
    except Exception as e:
        log.debug( "Dropping repository_rating_association table failed: %s" % str( e ) )
    try:
        RepositoryCategoryAssociation_table.drop()
    except Exception as e:
        log.debug( "Dropping repository_category_association table failed: %s" % str( e ) )
