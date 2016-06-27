"""
Migration script to add the installed_changeset_revision column to the tool_shed_repository table.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Column, MetaData, Table

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    col = Column( "installed_changeset_revision", TrimmedString( 255 ) )
    try:
        col.create( ToolShedRepository_table )
        assert col is ToolShedRepository_table.c.installed_changeset_revision
    except Exception as e:
        print("Adding installed_changeset_revision column to the tool_shed_repository table failed: %s" % str( e ))
        log.debug( "Adding installed_changeset_revision column to the tool_shed_repository table failed: %s" % str( e ) )
    # Update each row by setting the value of installed_changeset_revison to be the value of changeset_revision.
    # This will be problematic if the value of changeset_revision was updated to something other than the value
    # that it was when the repository was installed (because the install path determined in real time will attempt to
    # find the repository using the updated changeset_revison instead of the required installed_changeset_revision),
    # but at the time this script was written, this scenario is extremely unlikely.
    cmd = "SELECT id AS id, " \
        + "installed_changeset_revision AS installed_changeset_revision, " \
        + "changeset_revision AS changeset_revision " \
        + "FROM tool_shed_repository;"
    tool_shed_repositories = migrate_engine.execute( cmd ).fetchall()
    update_count = 0
    for row in tool_shed_repositories:
        cmd = "UPDATE tool_shed_repository " \
            + "SET installed_changeset_revision = '%s' " % row.changeset_revision \
            + "WHERE changeset_revision = '%s';" % row.changeset_revision
        migrate_engine.execute( cmd )
        update_count += 1
    print("Updated the installed_changeset_revision column for ", update_count, " rows in the tool_shed_repository table.  ")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    try:
        ToolShedRepository_table.c.installed_changeset_revision.drop()
    except Exception as e:
        print("Dropping column installed_changeset_revision from the tool_shed_repository table failed: %s" % str( e ))
        log.debug( "Dropping column installed_changeset_revision from the tool_shed_repository table failed: %s" % str( e ) )
