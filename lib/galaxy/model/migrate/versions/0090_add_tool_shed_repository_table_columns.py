"""
Migration script to add the uninstalled and dist_to_shed columns to the tool_shed_repository table.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Boolean, Column, MetaData, Table

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def default_false(migrate_engine):
    if migrate_engine.name in ['mysql', 'sqlite']:
        return "0"
    elif migrate_engine.name in ['postgres', 'postgresql']:
        return "false"


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    c = Column( "uninstalled", Boolean, default=False )
    try:
        c.create( ToolShedRepository_table )
        assert c is ToolShedRepository_table.c.uninstalled
        migrate_engine.execute( "UPDATE tool_shed_repository SET uninstalled=%s" % default_false(migrate_engine) )
    except Exception as e:
        print("Adding uninstalled column to the tool_shed_repository table failed: %s" % str( e ))
    c = Column( "dist_to_shed", Boolean, default=False )
    try:
        c.create( ToolShedRepository_table )
        assert c is ToolShedRepository_table.c.dist_to_shed
        migrate_engine.execute( "UPDATE tool_shed_repository SET dist_to_shed=%s" % default_false(migrate_engine) )
    except Exception as e:
        print("Adding dist_to_shed column to the tool_shed_repository table failed: %s" % str( e ))


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    try:
        ToolShedRepository_table.c.uninstalled.drop()
    except Exception as e:
        print("Dropping column uninstalled from the tool_shed_repository table failed: %s" % str( e ))
    try:
        ToolShedRepository_table.c.dist_to_shed.drop()
    except Exception as e:
        print("Dropping column dist_to_shed from the tool_shed_repository table failed: %s" % str( e ))
