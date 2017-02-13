"""Migration script to add status and error_message columns to the tool_shed_repository table."""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table, TEXT

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    # Add the status column to the tool_shed_repository table.
    col = Column( "status", TrimmedString( 255 ) )
    try:
        col.create( ToolShedRepository_table )
        assert col is ToolShedRepository_table.c.status
    except Exception:
        log.exception("Adding status column to the tool_shed_repository table failed.")
    # Add the error_message column to the tool_shed_repository table.
    col = Column( "error_message", TEXT )
    try:
        col.create( ToolShedRepository_table )
        assert col is ToolShedRepository_table.c.error_message
    except Exception:
        log.exception("Adding error_message column to the tool_shed_repository table failed.")
    # Update the status column value for tool_shed_repositories to the default value 'Installed'.
    cmd = "UPDATE tool_shed_repository SET status = 'Installed';"
    try:
        migrate_engine.execute( cmd )
    except Exception:
        log.exception("Exception executing SQL command: %s" % cmd)
    # Update the status column for tool_shed_repositories that have been uninstalled.
    cmd = "UPDATE tool_shed_repository SET status = 'Uninstalled' WHERE uninstalled;"
    try:
        migrate_engine.execute( cmd )
    except Exception:
        log.exception("Exception executing SQL command: %s" % cmd)
    # Update the status column for tool_shed_repositories that have been deactivated.
    cmd = "UPDATE tool_shed_repository SET status = 'Deactivated' where deleted and not uninstalled;"
    try:
        migrate_engine.execute( cmd )
    except Exception:
        log.exception("Exception executing SQL command: %s" % cmd)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    try:
        ToolShedRepository_table.c.status.drop()
    except Exception:
        log.exception("Dropping column status from the tool_shed_repository table failed.")
    try:
        ToolShedRepository_table.c.error_message.drop()
    except Exception:
        log.exception("Dropping column error_message from the tool_shed_repository table failed.")
