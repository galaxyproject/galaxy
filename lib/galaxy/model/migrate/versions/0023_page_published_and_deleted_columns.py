"""
Migration script to add columns for tracking whether pages are deleted and
publicly accessible.
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
    
    Page_table = Table( "page", metadata, autoload=True )
    
    c = Column( "published", Boolean, index=True, default=False )
    c.create( Page_table )
    assert c is Page_table.c.published
    
    c = Column( "deleted", Boolean, index=True, default=False ) 
    c.create( Page_table )
    assert c is Page_table.c.deleted

def downgrade():
    metadata.reflect()

    Page_table = Table( "page", metadata, autoload=True )
    Page_table.c.published.drop()
    Page_table.c.deleted.drop()
