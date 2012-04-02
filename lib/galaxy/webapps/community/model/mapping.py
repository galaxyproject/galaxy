"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here. 
"""
import logging
log = logging.getLogger( __name__ )

import sys
import datetime

from galaxy.webapps.community.model import *
from galaxy.model.orm import *
from galaxy.model.orm.ext.assignmapper import *
from galaxy.model.custom_types import *
from galaxy.util.bunch import Bunch
from galaxy.util.shed_util import ShedCounter
from galaxy.webapps.community.security import CommunityRBACAgent

metadata = MetaData()
context = Session = scoped_session( sessionmaker( autoflush=False, autocommit=True ) )

# For backward compatibility with "context.current"
context.current = Session

dialect_to_egg = { 
    "sqlite"   : "pysqlite>=2",
    "postgres" : "psycopg2",
    "mysql"    : "MySQL_python"
}

# NOTE REGARDING TIMESTAMPS:
#   It is currently difficult to have the timestamps calculated by the 
#   database in a portable way, so we're doing it in the client. This
#   also saves us from needing to postfetch on postgres. HOWEVER: it
#   relies on the client's clock being set correctly, so if clustering
#   web servers, use a time server to ensure synchronization

# Return the current time in UTC without any timezone information
now = datetime.datetime.utcnow

User.table = Table( "galaxy_user", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "email", TrimmedString( 255 ), nullable=False ),
    Column( "username", String( 255 ), index=True ),
    Column( "password", TrimmedString( 40 ), nullable=False ),
    Column( "external", Boolean, default=False ),
    Column( "new_repo_alert", Boolean, default=False ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

Group.table = Table( "galaxy_group", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

Role.table = Table( "role", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "description", TEXT ),
    Column( "type", String( 40 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

UserGroupAssociation.table = Table( "user_group_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

UserRoleAssociation.table = Table( "user_role_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

GroupRoleAssociation.table = Table( "group_role_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

GalaxySession.table = Table( "galaxy_session", metadata,
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

Repository.table = Table( "repository", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), index=True ),
    Column( "description" , TEXT ),
    Column( "long_description" , TEXT ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "private", Boolean, default=False ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "email_alerts", JSONType, nullable=True ),
    Column( "times_downloaded", Integer ) )

RepositoryMetadata.table = Table( "repository_metadata", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
    Column( "changeset_revision", TrimmedString( 255 ), index=True ),
    Column( "metadata", JSONType, nullable=True ),
    Column( "tool_versions", JSONType, nullable=True ),
    Column( "malicious", Boolean, default=False ) )

RepositoryRatingAssociation.table = Table( "repository_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True ),
    Column( "comment", TEXT ) )

RepositoryCategoryAssociation.table = Table( "repository_category_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
    Column( "category_id", Integer, ForeignKey( "category.id" ), index=True ) )

Category.table = Table( "category", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), index=True, unique=True ),
    Column( "description" , TEXT ),
    Column( "deleted", Boolean, index=True, default=False ) )

Tag.table = Table( "tag", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "type", Integer ),
    Column( "parent_id", Integer, ForeignKey( "tag.id" ) ),
    Column( "name", TrimmedString(255) ), 
    UniqueConstraint( "name" ) )

# With the tables defined we can define the mappers and setup the relationships between the model objects.
assign_mapper( context, User, User.table, 
    properties=dict( active_repositories=relation( Repository, primaryjoin=( ( Repository.table.c.user_id == User.table.c.id ) & ( not_( Repository.table.c.deleted ) ) ), order_by=( Repository.table.c.name ) ),
                     galaxy_sessions=relation( GalaxySession, order_by=desc( GalaxySession.table.c.update_time ) ) ) )

assign_mapper( context, Group, Group.table,
    properties=dict( users=relation( UserGroupAssociation ) ) )

assign_mapper( context, Role, Role.table,
    properties=dict(
        users=relation( UserRoleAssociation ),
        groups=relation( GroupRoleAssociation ) ) )

assign_mapper( context, UserGroupAssociation, UserGroupAssociation.table,
    properties=dict( user=relation( User, backref = "groups" ),
                     group=relation( Group, backref = "members" ) ) )

assign_mapper( context, UserRoleAssociation, UserRoleAssociation.table,
    properties=dict(
        user=relation( User, backref="roles" ),
        non_private_roles=relation( User, 
                                    backref="non_private_roles",
                                    primaryjoin=( ( User.table.c.id == UserRoleAssociation.table.c.user_id ) & ( UserRoleAssociation.table.c.role_id == Role.table.c.id ) & not_( Role.table.c.name == User.table.c.email ) ) ),
        role=relation( Role ) ) )

assign_mapper( context, GroupRoleAssociation, GroupRoleAssociation.table,
    properties=dict(
        group=relation( Group, backref="roles" ),
        role=relation( Role ) ) )

assign_mapper( context, GalaxySession, GalaxySession.table,
    properties=dict( user=relation( User.mapper ) ) )

assign_mapper( context, Tag, Tag.table,
    properties=dict( children=relation(Tag, backref=backref( 'parent', remote_side=[Tag.table.c.id] ) ) ) )

assign_mapper( context, Category, Category.table,
    properties=dict( repositories=relation( RepositoryCategoryAssociation ) ) )

assign_mapper( context, Repository, Repository.table, 
    properties = dict(
        categories=relation( RepositoryCategoryAssociation ),
        ratings=relation( RepositoryRatingAssociation, order_by=desc( RepositoryRatingAssociation.table.c.update_time ), backref="repositories" ),
        user=relation( User.mapper ),
        downloadable_revisions=relation( RepositoryMetadata, order_by=desc( RepositoryMetadata.table.c.update_time ) ) ) )

assign_mapper( context, RepositoryMetadata, RepositoryMetadata.table,
    properties=dict( repository=relation( Repository ) ) )

assign_mapper( context, RepositoryRatingAssociation, RepositoryRatingAssociation.table,
    properties=dict( repository=relation( Repository ), user=relation( User ) ) )

assign_mapper( context, RepositoryCategoryAssociation, RepositoryCategoryAssociation.table,
    properties=dict(
        category=relation( Category ),
        repository=relation( Repository ) ) )

def guess_dialect_for_url( url ):
    return (url.split(':', 1))[0]

def load_egg_for_url( url ):
    # Load the appropriate db module
    dialect = guess_dialect_for_url( url )
    try:
        egg = dialect_to_egg[dialect]
        try:
            pkg_resources.require( egg )
            log.debug( "%s egg successfully loaded for %s dialect" % ( egg, dialect ) )
        except:
            # If the module's in the path elsewhere (i.e. non-egg), it'll still load.
            log.warning( "%s egg not found, but an attempt will be made to use %s anyway" % ( egg, dialect ) )
    except KeyError:
        # Let this go, it could possibly work with db's we don't support
        log.error( "database_connection contains an unknown SQLAlchemy database dialect: %s" % dialect )

def init( file_path, url, engine_options={}, create_tables=False ):
    """Connect mappings to the database"""
    # Load the appropriate db module
    load_egg_for_url( url )
    # Create the database engine
    engine = create_engine( url, **engine_options )
    # Connect the metadata to the database.
    metadata.bind = engine
    # Clear any existing contextual sessions and reconfigure
    Session.remove()
    Session.configure( bind=engine )
    # Create tables if needed
    if create_tables:
        metadata.create_all()
    # Pack everything into a bunch
    result = Bunch( **globals() )
    result.engine = engine
    result.session = Session
    result.create_tables = create_tables
    #load local galaxy security policy
    result.security_agent = CommunityRBACAgent( result )
    result.shed_counter = ShedCounter( result )
    return result
