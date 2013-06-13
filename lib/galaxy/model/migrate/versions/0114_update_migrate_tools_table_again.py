"""
Migration script to update the migrate_tools.repository_path column to point to the new location lib/tool_shed/galaxy_install/migrate.
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


def upgrade(migrate_engine):
    print __doc__
    # Create the table.
    try:
        cmd = "UPDATE migrate_tools set repository_path='lib/tool_shed/galaxy_install/migrate';"
        migrate_engine.execute( cmd )
    except Exception, e:
        log.debug( "Updating migrate_tools.repository_path column to point to the new location lib/tool_shed/galaxy_install/migrate failed: %s" % str( e ) )

def downgrade(migrate_engine):
    try:
        cmd = "UPDATE migrate_tools set repository_path='lib/galaxy/tool_shed/migrate';"
        migrate_engine.execute( cmd )
    except Exception, e:
        log.debug( "Updating migrate_tools.repository_path column to point to the old location lib/galaxy/tool_shed/migrate failed: %s" % str( e ) )

