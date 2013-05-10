"""
Migration script to add the metadata, update_available and includes_datatypes columns to the tool_shed_repository table.
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

metadata = MetaData()

def get_default_false(migrate_engine):
    if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
        return "0"
    elif migrate_engine.name in ['postgresql', 'postgres']:
        return "false"

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    c = Column( "metadata", JSONType(), nullable=True )
    try:
        c.create( ToolShedRepository_table )
        assert c is ToolShedRepository_table.c.metadata
    except Exception, e:
        print "Adding metadata column to the tool_shed_repository table failed: %s" % str( e )
        log.debug( "Adding metadata column to the tool_shed_repository table failed: %s" % str( e ) )
    c = Column( "includes_datatypes", Boolean, index=True, default=False )
    try:
        c.create( ToolShedRepository_table, index_name="ix_tool_shed_repository_includes_datatypes")
        assert c is ToolShedRepository_table.c.includes_datatypes
        migrate_engine.execute( "UPDATE tool_shed_repository SET includes_datatypes=%s" % get_default_false(migrate_engine))
    except Exception, e:
        print "Adding includes_datatypes column to the tool_shed_repository table failed: %s" % str( e )
        log.debug( "Adding includes_datatypes column to the tool_shed_repository table failed: %s" % str( e ) )
    c = Column( "update_available", Boolean, default=False )
    try:
        c.create( ToolShedRepository_table )
        assert c is ToolShedRepository_table.c.update_available
        migrate_engine.execute( "UPDATE tool_shed_repository SET update_available=%s" % get_default_false(migrate_engine))
    except Exception, e:
        print "Adding update_available column to the tool_shed_repository table failed: %s" % str( e )
        log.debug( "Adding update_available column to the tool_shed_repository table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    try:
        ToolShedRepository_table.c.metadata.drop()
    except Exception, e:
        print "Dropping column metadata from the tool_shed_repository table failed: %s" % str( e )
        log.debug( "Dropping column metadata from the tool_shed_repository table failed: %s" % str( e ) )
    try:
        ToolShedRepository_table.c.includes_datatypes.drop()
    except Exception, e:
        print "Dropping column includes_datatypes from the tool_shed_repository table failed: %s" % str( e )
        log.debug( "Dropping column includes_datatypes from the tool_shed_repository table failed: %s" % str( e ) )
    try:
        ToolShedRepository_table.c.update_available.drop()
    except Exception, e:
        print "Dropping column update_available from the tool_shed_repository table failed: %s" % str( e )
        log.debug( "Dropping column update_available from the tool_shed_repository table failed: %s" % str( e ) )
