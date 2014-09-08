"""
Migration script to create the tool_version and tool_version_association tables and drop the tool_id_guid_map table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow
# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *
from galaxy.model.custom_types import _sniffnfix_pg9_hex
from galaxy.util.json import loads, dumps

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()
#migrate_engine = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def nextval( table, col='id' ):
    if migrate_engine.name == 'postgres':
        return "nextval('%s_%s_seq')" % ( table, col )
    elif migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
        return "null"
    else:
        raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )

def localtimestamp():
   if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
       return "LOCALTIMESTAMP"
   elif migrate_engine.name == 'sqlite':
       return "current_date || ' ' || current_time"
   else:
       raise Exception( 'Unable to convert data for unknown database type: %s' % db )

ToolVersion_table = Table( "tool_version", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "tool_id", String( 255 ) ),
    Column( "tool_shed_repository_id", Integer, ForeignKey( "tool_shed_repository.id" ), index=True, nullable=True ) )

ToolVersionAssociation_table = Table( "tool_version_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "tool_id", Integer, ForeignKey( "tool_version.id" ), index=True, nullable=False ),
    Column( "parent_id", Integer, ForeignKey( "tool_version.id" ), index=True, nullable=False ) )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__

    ToolIdGuidMap_table = Table( "tool_id_guid_map", metadata, autoload=True )

    metadata.reflect()
    # Create the tables.
    try:
        ToolVersion_table.create()
    except Exception, e:
        log.debug( "Creating tool_version table failed: %s" % str( e ) )
    try:
        ToolVersionAssociation_table.create()
    except Exception, e:
        log.debug( "Creating tool_version_association table failed: %s" % str( e ) )
    # Populate the tool table with tools included in installed tool shed repositories.
    cmd = "SELECT id, metadata FROM tool_shed_repository"
    result = migrate_engine.execute( cmd )
    count = 0
    for row in result:
        if row[1]:
            tool_shed_repository_id = row[0]
            repository_metadata = loads( _sniffnfix_pg9_hex( str( row[1] ) ) )
            # Create a new row in the tool table for each tool included in repository.  We will NOT
            # handle tool_version_associaions because we do not have the information we need to do so.
            tools = repository_metadata.get( 'tools', [] )
            for tool_dict in tools:
                cmd = "INSERT INTO tool_version VALUES (%s, %s, %s, '%s', %s)" % \
                    ( nextval( 'tool_version' ), localtimestamp(), localtimestamp(), tool_dict[ 'guid' ], tool_shed_repository_id )
                migrate_engine.execute( cmd )
                count += 1
    print "Added %d rows to the new tool_version table." % count
    # Drop the tool_id_guid_map table since the 2 new tables render it unnecessary.
    try:
        ToolIdGuidMap_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_id_guid_map table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine

    ToolIdGuidMap_table = Table( "tool_id_guid_map", metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "create_time", DateTime, default=now ),
        Column( "update_time", DateTime, default=now, onupdate=now ),
        Column( "tool_id", String( 255 ) ),
        Column( "tool_version", TEXT ),
        Column( "tool_shed", TrimmedString( 255 ) ),
        Column( "repository_owner", TrimmedString( 255 ) ),
        Column( "repository_name", TrimmedString( 255 ) ),
        Column( "guid", TEXT, index=True, unique=True ) )

    metadata.reflect()
    try:
        ToolVersionAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_version_association table failed: %s" % str( e ) )
    try:
        ToolVersion_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_version table failed: %s" % str( e ) )
    try:
        ToolIdGuidMap_table.create()
    except Exception, e:
        log.debug( "Creating tool_id_guid_map table failed: %s" % str( e ) )
