"""
Migration script to add support for storing visualizations.
  1) Creates Visualization and VisualizationRevision tables
"""

from sqlalchemy import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

Visualization_table = Table( "visualization", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "latest_revision_id", Integer,
            ForeignKey( "visualization_revision.id", use_alter=True, name='visualization_latest_revision_id_fk' ), index=True ),
    Column( "title", TEXT ),
    Column( "type", TEXT )
    )

VisualizationRevision_table = Table( "visualization_revision", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True, nullable=False ),
    Column( "title", TEXT ),
    Column( "config", TEXT )
    )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        Visualization_table.create()
    except:
        log.debug( "Could not create page table" )
    try:
        VisualizationRevision_table.create()
    except:
        log.debug( "Could not create page_revision table" )


def downgrade():
    metadata.reflect()
    Visualization_table.drop()
    VisualizationRevision_table.drop()

