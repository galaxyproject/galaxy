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

metadata = MetaData()

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

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    try:
        if migrate_engine.name == 'mysql':
            # Strip slug index prior to creation so we can do it manually.
            slug_index = None
            for ix in Page_table.indexes:
                if ix.name == 'ix_page_slug':
                    slug_index = ix
            Page_table.indexes.remove(slug_index)
        Page_table.create()
        if migrate_engine.name == 'mysql':
            # Create slug index manually afterward.
            i = Index( "ix_page_slug", Page_table.c.slug, mysql_length = 200)
            i.create()
    except Exception, ex:
        log.debug(ex)
        log.debug( "Could not create page table" )
    try:
        PageRevision_table.create()
    except:
        log.debug( "Could not create page_revision table" )

    # Add 1 column to the user table
    User_table = Table( "galaxy_user", metadata, autoload=True )
    col = Column( 'username', String(255), index=True, unique=True, default=False )
    col.create( User_table, index_name='ix_user_username', unique_name='username' )
    assert col is User_table.c.username

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    Page_table.drop()
    PageRevision_table.drop()
    User_table = Table( "galaxy_user", metadata, autoload=True )
    User_table.c.username.drop()
