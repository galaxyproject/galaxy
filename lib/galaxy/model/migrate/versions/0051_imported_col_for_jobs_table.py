"""
Migration script to add imported column for jobs table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    # Create and initialize imported column in job table.
    Jobs_table = Table( "job", metadata, autoload=True )
    c = Column( "imported", Boolean, default=False, index=True )
    try:
        # Create
        c.create( Jobs_table, index_name="ix_job_imported")
        assert c is Jobs_table.c.imported

        # Initialize.
        if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
            default_false = "0"
        elif migrate_engine.name in ['postgres', 'postgresql']:
            default_false = "false"
        migrate_engine.execute( "UPDATE job SET imported=%s" % default_false )

    except Exception, e:
        print "Adding imported column to job table failed: %s" % str( e )
        log.debug( "Adding imported column to job table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop imported column from job table.
    Jobs_table = Table( "job", metadata, autoload=True )
    try:
        Jobs_table.c.imported.drop()
    except Exception, e:
        print "Dropping column imported from job table failed: %s" % str( e )
        log.debug( "Dropping column imported from job table failed: %s" % str( e ) )
