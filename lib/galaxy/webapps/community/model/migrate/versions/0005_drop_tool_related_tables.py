"""
Drops the tool, tool_category_association, event, tool_event_association, tool_rating_association,
tool_tag_association and tool_annotation_association tables since they are no longer used in the 
next-gen tool shed.
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
log.setLevel( logging.DEBUG )
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def upgrade():
    print __doc__
    # Load existing tables
    metadata.reflect()
    # Load and then drop the tool_category_association table
    try:
        ToolCategoryAssociation_table = Table( "tool_category_association", metadata, autoload=True )
    except NoSuchTableError:
        log.debug( "Failed loading table tool_category_association" )
    try:
        ToolCategoryAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_category_association table failed: %s" % str( e ) )
    # Load and then drop the tool_event_association table
    try:
        ToolEventAssociation_table = Table( "tool_event_association", metadata, autoload=True )
    except NoSuchTableError:
        log.debug( "Failed loading table tool_event_association" )
    try:
        ToolEventAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_event_association table failed: %s" % str( e ) )
    # Load and then drop the tool_rating_association table
    try:
        ToolRatingAssociation_table = Table( "tool_rating_association", metadata, autoload=True )
    except NoSuchTableError:
        log.debug( "Failed loading table tool_rating_association" )
    try:
        ToolRatingAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_rating_association table failed: %s" % str( e ) )
    # Load and then drop the tool_tag_association table
    try:
        ToolTagAssociation_table = Table( "tool_tag_association", metadata, autoload=True )
    except NoSuchTableError:
        log.debug( "Failed loading table tool_tag_association" )
    try:
        ToolTagAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_tag_association table failed: %s" % str( e ) )
    # Load and then drop the tool_annotation_association table
    try:
        ToolAnnotationAssociation_table = Table( "tool_annotation_association", metadata, autoload=True )
    except NoSuchTableError:
        log.debug( "Failed loading table tool_annotation_association" )
    try:
        ToolAnnotationAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_annotation_association table failed: %s" % str( e ) )
    # Load and then drop the event table
    try:
        Event_table = Table( "event", metadata, autoload=True )
    except NoSuchTableError:
        log.debug( "Failed loading table event" )
    try:
        Event_table.drop()
    except Exception, e:
        log.debug( "Dropping event table failed: %s" % str( e ) )
    # Load and then drop the tool table
    try:
        Tool_table = Table( "tool", metadata, autoload=True )
    except NoSuchTableError:
        log.debug( "Failed loading table tool" )
    try:
        Tool_table.drop()
    except Exception, e:
        log.debug( "Dropping tool table failed: %s" % str( e ) )
def downgrade():
    # Load existing tables
    metadata.reflect()
    # We've lost all of our data, so downgrading is useless. However, we'll
    # at least re-create the dropped tables.
    Event_table = Table( 'event', metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "create_time", DateTime, default=now ),
        Column( "update_time", DateTime, default=now, onupdate=now ),
        Column( "state", TrimmedString( 255 ), index=True ),
        Column( "comment", TEXT ) )

    Tool_table = Table( "tool", metadata, 
        Column( "id", Integer, primary_key=True ),
        Column( "guid", TrimmedString( 255 ), index=True, unique=True ),
        Column( "tool_id", TrimmedString( 255 ), index=True ),
        Column( "create_time", DateTime, default=now ),
        Column( "update_time", DateTime, default=now, onupdate=now ),
        Column( "newer_version_id", Integer, ForeignKey( "tool.id" ), nullable=True ),
        Column( "name", TrimmedString( 255 ), index=True ),
        Column( "description" , TEXT ),
        Column( "user_description" , TEXT ),
        Column( "version", TrimmedString( 255 ) ),
        Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
        Column( "external_filename" , TEXT ),
        Column( "deleted", Boolean, index=True, default=False ),
        Column( "suite", Boolean, default=False, index=True ) )

    ToolCategoryAssociation_table = Table( "tool_category_association", metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "tool_id", Integer, ForeignKey( "tool.id" ), index=True ),
        Column( "category_id", Integer, ForeignKey( "category.id" ), index=True ) )

    ToolEventAssociation_table = Table( "tool_event_association", metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "tool_id", Integer, ForeignKey( "tool.id" ), index=True ),
        Column( "event_id", Integer, ForeignKey( "event.id" ), index=True ) )

    ToolRatingAssociation_table = Table( "tool_rating_association", metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "create_time", DateTime, default=now ),
        Column( "update_time", DateTime, default=now, onupdate=now ),
        Column( "tool_id", Integer, ForeignKey( "tool.id" ), index=True ),
        Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
        Column( "rating", Integer, index=True ),
        Column( "comment", TEXT ) )

    ToolTagAssociation_table = Table( "tool_tag_association", metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "tool_id", Integer, ForeignKey( "tool.id" ), index=True ),
        Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
        Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
        Column( "user_tname", TrimmedString(255), index=True),
        Column( "value", TrimmedString(255), index=True),
        Column( "user_value", TrimmedString(255), index=True) )

    ToolAnnotationAssociation_table = Table( "tool_annotation_association", metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "tool_id", Integer, ForeignKey( "tool.id" ), index=True ),
        Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
        Column( "annotation", TEXT, index=True) )

    # Create the event table
    try:
        Event_table.create()
    except Exception, e:
        log.debug( "Creating event table failed: %s" % str( e ) )
    # Create the tool table
    try:
        Tool_table.create()
    except Exception, e:
        log.debug( "Creating tool table failed: %s" % str( e ) )
    # Create the tool_category_association table
    try:
        ToolCategoryAssociation_table.create()
    except Exception, e:
        log.debug( "Creating tool_category_association table failed: %s" % str( e ) )
    # Create the tool_event_association table
    try:
        ToolEventAssociation_table.create()
    except Exception, e:
        log.debug( "Creating tool_event_association table failed: %s" % str( e ) )
    # Create the tool_rating_association table
    try:
        ToolRatingAssociation_table.create()
    except Exception, e:
        log.debug( "Creating tool_rating_association table failed: %s" % str( e ) )
    # Create the tool_tag_association table
    try:
        ToolTagAssociation_table.create()
    except Exception, e:
        log.debug( "Creating tool_tag_association table failed: %s" % str( e ) )
    # Create the tool_annotation_association table
    try:
        ToolAnnotationAssociation_table.create()
    except Exception, e:
        log.debug( "Creating tool_annotation_association table failed: %s" % str( e ) )
