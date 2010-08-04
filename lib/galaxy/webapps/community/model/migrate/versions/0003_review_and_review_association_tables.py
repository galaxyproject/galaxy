"""
Adds the tool_rating_association table, enabling tools to be rated along with review comments.
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

ToolRatingAssociation_table = Table( "tool_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "tool_id", Integer, ForeignKey( "tool.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True ),
    Column( "comment", TEXT ) )

def upgrade():
    print __doc__
    # Load existing tables
    metadata.reflect()
    try:
        ToolRatingAssociation_table.create()
    except Exception, e:
        log.debug( "Creating tool_rating_association table failed: %s" % str( e ) )  
def downgrade():
    # Load existing tables
    metadata.reflect()
    try:
        ToolRatingAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_rating_association table failed: %s" % str( e ) )  
