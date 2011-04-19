"""
Migration script to create table for storing tool tag associations.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

from galaxy.model.custom_types import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

# Table to add

ToolTagAssociation_table = Table( "tool_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "tool_id", TrimmedString(255), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

def upgrade():
    print __doc__
    metadata.reflect()
    
    # Create tool_tag_association table
    try:
        ToolTagAssociation_table.create()
    except Exception, e:
        log.error( "Creating tool_tag_association table failed: %s" % str( e ) )
        
def downgrade():
    metadata.reflect()
    
    # Drop tool_tag_association table
    try:
        ToolTagAssociation_table.drop()
    except Exception, e:
        log.error( "Dropping tool_tag_association table failed: %s" % str( e ) )
