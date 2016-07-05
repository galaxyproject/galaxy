"""
Migration script to add necessary columns for distinguishing between viewing/importing and publishing histories, \
workflows, and pages. Script adds published column to histories and workflows and importable column to pages.
"""
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, Index, MetaData, Table

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create published column in history table.
    History_table = Table( "history", metadata, autoload=True )
    c = Column( "published", Boolean, index=True )
    try:
        c.create( History_table, index_name='ix_history_published')
        assert c is History_table.c.published
    except Exception as e:
        print("Adding published column to history table failed: %s" % str( e ))
        log.debug( "Adding published column to history table failed: %s" % str( e ) )

    if migrate_engine.name != 'sqlite':
        # Create index for published column in history table.
        try:
            i = Index( "ix_history_published", History_table.c.published )
            i.create()
        except:
            # Mysql doesn't have a named index, but alter should work
            History_table.c.published.alter( unique=False )

    # Create published column in stored workflows table.
    StoredWorkflow_table = Table( "stored_workflow", metadata, autoload=True )
    c = Column( "published", Boolean, index=True )
    try:
        c.create( StoredWorkflow_table, index_name='ix_stored_workflow_published')
        assert c is StoredWorkflow_table.c.published
    except Exception as e:
        print("Adding published column to stored_workflow table failed: %s" % str( e ))
        log.debug( "Adding published column to stored_workflow table failed: %s" % str( e ) )

    if migrate_engine.name != 'sqlite':
        # Create index for published column in stored workflows table.
        try:
            i = Index( "ix_stored_workflow_published", StoredWorkflow_table.c.published )
            i.create()
        except:
            # Mysql doesn't have a named index, but alter should work
            StoredWorkflow_table.c.published.alter( unique=False )

    # Create importable column in page table.
    Page_table = Table( "page", metadata, autoload=True )
    c = Column( "importable", Boolean, index=True )
    try:
        c.create( Page_table, index_name='ix_page_importable')
        assert c is Page_table.c.importable
    except Exception as e:
        print("Adding importable column to page table failed: %s" % str( e ))
        log.debug( "Adding importable column to page table failed: %s" % str( e ) )

    if migrate_engine.name != 'sqlite':
        # Create index for importable column in page table.
        try:
            i = Index( "ix_page_importable", Page_table.c.importable )
            i.create()
        except:
            # Mysql doesn't have a named index, but alter should work
            Page_table.c.importable.alter( unique=False )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop published column from history table.
    History_table = Table( "history", metadata, autoload=True )
    try:
        History_table.c.published.drop()
    except Exception as e:
        print("Dropping column published from history table failed: %s" % str( e ))
        log.debug( "Dropping column published from history table failed: %s" % str( e ) )

    # Drop published column from stored_workflow table.
    StoredWorkflow_table = Table( "stored_workflow", metadata, autoload=True )
    try:
        StoredWorkflow_table.c.published.drop()
    except Exception as e:
        print("Dropping column published from stored_workflow table failed: %s" % str( e ))
        log.debug( "Dropping column published from stored_workflow table failed: %s" % str( e ) )

    # Drop importable column from page table.
    Page_table = Table( "page", metadata, autoload=True )
    try:
        Page_table.c.importable.drop()
    except Exception as e:
        print("Dropping column importable from page table failed: %s" % str( e ))
        log.debug( "Dropping column importable from page table failed: %s" % str( e ) )
