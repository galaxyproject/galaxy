"""
Migration script to add support for "Pages".
  1) Creates Page and PageRevision tables
  2) Adds username column to User table
"""

from sqlalchemy import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

Page_table = Table( "page", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "latest_revision_id", Integer,
            ForeignKey( "page_revision.id", use_alter=True, name='page_latest_revision_id_fk' ), index=True ),
    Column( "title", TEXT ),
    Column( "slug", TEXT, unique=True, index=True ),
    )

PageRevision_table = Table( "page_revision", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True, nullable=False ),
    Column( "title", TEXT ),
    Column( "content", TEXT )
    )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        Page_table.create()
    except:
        log.debug( "Could not create page table" )
    try:
        PageRevision_table.create()
    except:
        log.debug( "Could not create page_revision table" )
    
    # Add 1 column to the user table
    User_table = Table( "galaxy_user", metadata, autoload=True )
    col = Column( 'username', String(255), index=True, unique=True, default=False )
    col.create( User_table )
    assert col is User_table.c.username

def downgrade():
    metadata.reflect()
    Page_table.drop()
    PageRevision_table.drop()
    User_table = Table( "galaxy_user", metadata, autoload=True )
    User_table.c.username.drop()
