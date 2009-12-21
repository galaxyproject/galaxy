"""
Migration script to add column for a history slug.
"""

from sqlalchemy import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

def upgrade():
    
    print __doc__
    metadata.reflect()
    
    History_table = Table( "history", metadata, autoload=True )
    
    # Create slug column.
    c = Column( "slug", TEXT, index=True )
    c.create( History_table )
    assert c is History_table.c.slug
    
    # Create slug index.
    try:
        i = Index( "ix_history_slug", History_table.c.slug )
        i.create()
    except:
        # Mysql doesn't have a named index, but alter should work
        History_table.c.slug.alter( unique=False )

def downgrade():
    metadata.reflect()

    History_table = Table( "history", metadata, autoload=True )
    History_table.c.slug.drop()
