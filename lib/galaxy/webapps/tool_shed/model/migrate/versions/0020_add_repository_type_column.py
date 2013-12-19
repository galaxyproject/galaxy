"""Migration script to add the type column to the repository table."""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

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

metadata = MetaData()

def upgrade( migrate_engine ):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()
    Repository_table = Table( "repository", metadata, autoload=True )
    c = Column( "type", TrimmedString( 255 ), index=True )
    try:
        # Create
        c.create( Repository_table, index_name="ix_repository_type" )
        assert c is Repository_table.c.type
    except Exception, e:
        print "Adding type column to the repository table failed: %s" % str( e )
    # Update the type column to have the default unrestricted value.
    cmd = "UPDATE repository SET type = 'unrestricted'"
    migrate_engine.execute( cmd )

def downgrade( migrate_engine ):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop type column from repository table.
    Repository_table = Table( "repository", metadata, autoload=True )
    try:
        Repository_table.c.type.drop()
    except Exception, e:
        print "Dropping column type from the repository table failed: %s" % str( e )
