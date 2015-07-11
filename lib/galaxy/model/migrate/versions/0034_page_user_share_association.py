"""
Migration script to create a table for page-user share association.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

PageUserShareAssociation_table = Table( "page_user_share_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    # Create stored_workflow_tag_association table.
    try:
        PageUserShareAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating page_user_share_association table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop workflow_tag_association table.
    try:
        PageUserShareAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping page_user_share_association table failed: %s" % str( e ) )
