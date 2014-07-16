"""
Migration script to create initial tables.
"""

from sqlalchemy import *
from migrate import *

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

metadata = MetaData()

User_table = Table( "galaxy_user", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "email", TrimmedString( 255 ), nullable=False ),
    Column( "username", String( 255 ), index=True ),
    Column( "password", TrimmedString( 40 ), nullable=False ),
    Column( "external", Boolean, default=False ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

Group_table = Table( "galaxy_group", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

Role_table = Table( "role", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "description", TEXT ),
    Column( "type", String( 40 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

UserGroupAssociation_table = Table( "user_group_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

UserRoleAssociation_table = Table( "user_role_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

GroupRoleAssociation_table = Table( "group_role_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

GalaxySession_table = Table( "galaxy_session", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
    Column( "remote_host", String( 255 ) ),
    Column( "remote_addr", String( 255 ) ),
    Column( "referer", TEXT ),
    Column( "session_key", TrimmedString( 255 ), index=True, unique=True ), # unique 128 bit random number coerced to a string
    Column( "is_valid", Boolean, default=False ),
    Column( "prev_session_id", Integer ) # saves a reference to the previous session so we have a way to chain them together
    )

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
    Column( "deleted", Boolean, index=True, default=False ) )

Event_table = Table( 'event', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", TrimmedString( 255 ), index=True ),
    Column( "comment", TEXT ) )

ToolEventAssociation_table = Table( "tool_event_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "tool_id", Integer, ForeignKey( "tool.id" ), index=True ),
    Column( "event_id", Integer, ForeignKey( "event.id" ), index=True ) )

Category_table = Table( "category", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), index=True, unique=True ),
    Column( "description" , TEXT ),
    Column( "deleted", Boolean, index=True, default=False ) )

ToolCategoryAssociation_table = Table( "tool_category_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "tool_id", Integer, ForeignKey( "tool.id" ), index=True ),
    Column( "category_id", Integer, ForeignKey( "category.id" ), index=True ) )

Tag_table = Table( "tag", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "type", Integer ),
    Column( "parent_id", Integer, ForeignKey( "tag.id" ) ),
    Column( "name", TrimmedString(255) ),
    UniqueConstraint( "name" ) )

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
    Column( "annotation", TEXT ) )

def upgrade( migrate_engine ):
    print __doc__
    metadata.bind = migrate_engine
    metadata.create_all()
    Index( 'ix_tool_annotation_association_annotation', ToolAnnotationAssociation_table.c.annotation, mysql_length=767 ).create()

def downgrade( migrate_engine ):
    # Operations to reverse the above upgrade go here.
    pass
