"""
Migration script to alter the type of the tool_dependency.version column from TrimmedString(40) to Text.
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

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    ToolDependency_table = Table( "tool_dependency", metadata, autoload=True )
    # Change the tool_dependency table's version column from TrimmedString to Text.
    if migrate_engine.name in ['postgresql', 'postgres']:
        cmd = "ALTER TABLE tool_dependency ALTER COLUMN version TYPE Text;"
    elif migrate_engine.name == 'mysql':
        cmd = "ALTER TABLE tool_dependency MODIFY COLUMN version Text;"
    else:
        # We don't have to do anything for sqlite tables.  From the sqlite documentation at http://sqlite.org/datatype3.html:
        # 1.0 Storage Classes and Datatypes
        # Each value stored in an SQLite database (or manipulated by the database engine) has one of the following storage classes:
        # NULL. The value is a NULL value.
        # INTEGER. The value is a signed integer, stored in 1, 2, 3, 4, 6, or 8 bytes depending on the magnitude of the value.
        # REAL. The value is a floating point value, stored as an 8-byte IEEE floating point number.
        # TEXT. The value is a text string, stored using the database encoding (UTF-8, UTF-16BE or UTF-16LE).
        # BLOB. The value is a blob of data, stored exactly as it was input.
        cmd = None
    if cmd:
        try:
            migrate_engine.execute( cmd )
        except Exception, e:
            log.debug( "Altering tool_dependency.version column from TrimmedString(40) to Text failed: %s" % str( e ) )
def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    # Not necessary to change column type Text to TrimmedString(40).
    pass
