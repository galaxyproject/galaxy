"""
Migration script to add status and error_message columns to the tool_dependency table and drop the uninstalled column from the tool_dependency table.
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
#db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    ToolDependency_table = Table( "tool_dependency", metadata, autoload=True )
    col = Column( "status", TrimmedString( 255 ), nullable=False )
    try:
        col.create( ToolDependency_table )
        assert col is ToolDependency_table.c.status
    except Exception, e:
        print "Adding status column to the tool_dependency table failed: %s" % str( e )
    col = Column( "error_message", TEXT )
    try:
        col.create( ToolDependency_table )
        assert col is ToolDependency_table.c.error_message
    except Exception, e:
        print "Adding error_message column to the tool_dependency table failed: %s" % str( e )
    try:
        ToolDependency_table.c.uninstalled.drop()
    except Exception, e:
        print "Dropping uninstalled column from the tool_dependency table failed: %s" % str( e )
def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    ToolDependency_table = Table( "tool_dependency", metadata, autoload=True )
    try:
        ToolDependency_table.c.status.drop()
    except Exception, e:
        print "Dropping column status from the tool_dependency table failed: %s" % str( e )
    try:
        ToolDependency_table.c.error_message.drop()
    except Exception, e:
        print "Dropping column error_message from the tool_dependency table failed: %s" % str( e )
    col = Column( "uninstalled", Boolean, default=False )
    try:
        col.create( ToolDependency_table )
        assert col is ToolDependency_table.c.uninstalled
    except Exception, e:
        print "Adding uninstalled column to the tool_dependency table failed: %s" % str( e )
