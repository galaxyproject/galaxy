"""
Migration script to (a) create tables for annotating pages.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

PageAnnotationAssociation_table = Table( "page_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    # Create history_annotation_association table.
    try:
        PageAnnotationAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating page_annotation_association table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop page_annotation_association table.
    try:
        PageAnnotationAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping page_annotation_association table failed: %s" % str( e ) )

