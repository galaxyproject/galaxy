"""
Migration script to add the tool_versions column to the repository_metadata table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow
# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

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

def upgrade():
    print __doc__
    metadata.reflect()
    RepositoryMetadata_table = Table( "repository_metadata", metadata, autoload=True )
    c = Column( "tool_versions", JSONType, nullable=True )
    try:
        # Create
        c.create( RepositoryMetadata_table )
        assert c is RepositoryMetadata_table.c.tool_versions
    except Exception, e:
        print "Adding tool_versions column to the repository_metadata table failed: %s" % str( e )
    
def downgrade():
    metadata.reflect()
    # Drop new_repo_alert column from galaxy_user table.
    RepositoryMetadata_table = Table( "repository_metadata", metadata, autoload=True )
    try:
        RepositoryMetadata_table.c.tool_versions.drop()
    except Exception, e:
        print "Dropping column tool_versions from the repository_metadata table failed: %s" % str( e )
