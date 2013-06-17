"""
Migration script to add slug column for stored workflow.
"""

from sqlalchemy import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

def upgrade(migrate_engine):
    metadata.bind = migrate_engine

    print __doc__
    metadata.reflect()

    StoredWorkflow_table = Table( "stored_workflow", metadata, autoload=True )

    # Create slug column.
    c = Column( "slug", TEXT )
    c.create( StoredWorkflow_table )

    assert c is StoredWorkflow_table.c.slug

    # Create slug index.
    if migrate_engine.name != 'sqlite':
        try:
            i = Index( "ix_stored_workflow_slug", StoredWorkflow_table.c.slug, mysql_length = 200 )
            i.create()
        except:
            # Mysql doesn't have a named index, but alter should work
            StoredWorkflow_table.c.slug.alter( unique=False )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    StoredWorkflow_table = Table( "stored_workflow", metadata, autoload=True )
    StoredWorkflow_table.c.slug.drop()
