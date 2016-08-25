"""
Migration script to (a) add and populate necessary columns for doing community tagging of histories, datasets, and pages and \
(b) add table for doing individual and community tagging of workflows.

SQLite does not support 'ALTER TABLE ADD FOREIGN KEY', so this script will generate error messages when run against \
SQLite; however, script does execute successfully against SQLite.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Unicode

log = logging.getLogger( __name__ )
metadata = MetaData()

StoredWorkflowTagAssociation_table = Table( "stored_workflow_tag_association", metadata,
                                            Column( "id", Integer, primary_key=True ),
                                            Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
                                            Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
                                            Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                                            Column( "user_tname", Unicode(255), index=True),
                                            Column( "value", Unicode(255), index=True),
                                            Column( "user_value", Unicode(255), index=True) )

WorkflowTagAssociation_table = Table( "workflow_tag_association", metadata,
                                      Column( "id", Integer, primary_key=True ),
                                      Column( "workflow_id", Integer, ForeignKey( "workflow.id" ), index=True ),
                                      Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
                                      Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                                      Column( "user_tname", Unicode(255), index=True),
                                      Column( "value", Unicode(255), index=True),
                                      Column( "user_value", Unicode(255), index=True) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create user_id column in history_tag_association table.
    HistoryTagAssociation_table = Table( "history_tag_association", metadata, autoload=True )
    if migrate_engine.name != 'sqlite':
        c = Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
        try:
            c.create( HistoryTagAssociation_table, index_name='ix_history_tag_association_user_id')
            assert c is HistoryTagAssociation_table.c.user_id
        except Exception as e:
            # SQLite does not support 'ALTER TABLE ADD FOREIGN KEY', so catch exception if it arises.
            print(str(e))
            log.debug( "Adding user_id column to history_tag_association table failed: %s" % str( e ) )
    else:
        c = Column( "user_id", Integer)
        try:
            c.create( HistoryTagAssociation_table)
            assert c is HistoryTagAssociation_table.c.user_id
        except Exception as e:
            # SQLite does not support 'ALTER TABLE ADD FOREIGN KEY', so catch exception if it arises.
            print(str(e))
            log.debug( "Adding user_id column to history_tag_association table failed: %s" % str( e ) )

    # Populate column so that user_id is the id of the user who owns the history (and, up to now, was the only person able to tag the history).
    if c is HistoryTagAssociation_table.c.user_id:
        migrate_engine.execute(
            "UPDATE history_tag_association SET user_id=( SELECT user_id FROM history WHERE history_tag_association.history_id = history.id )" )

    if migrate_engine.name != 'sqlite':
        # Create user_id column in history_dataset_association_tag_association table.
        HistoryDatasetAssociationTagAssociation_table = Table( "history_dataset_association_tag_association", metadata, autoload=True )
        c = Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
        try:
            c.create( HistoryDatasetAssociationTagAssociation_table, index_name='ix_history_dataset_association_tag_association_user_id')
            assert c is HistoryDatasetAssociationTagAssociation_table.c.user_id
        except Exception as e:
            # SQLite does not support 'ALTER TABLE ADD FOREIGN KEY', so catch exception if it arises.
            print(str(e))
            log.debug( "Adding user_id column to history_dataset_association_tag_association table failed: %s" % str( e ) )
    else:
        # In sqlite, we can no longer quietly fail to add foreign key.
        # Create user_id column in history_dataset_association_tag_association table.
        HistoryDatasetAssociationTagAssociation_table = Table( "history_dataset_association_tag_association", metadata, autoload=True )
        c = Column( "user_id", Integer)
        try:
            c.create( HistoryDatasetAssociationTagAssociation_table)
            assert c is HistoryDatasetAssociationTagAssociation_table.c.user_id
        except Exception as e:
            # SQLite does not support 'ALTER TABLE ADD FOREIGN KEY', so catch exception if it arises.
            print(str(e))
            log.debug( "Adding user_id column to history_dataset_association_tag_association table failed: %s" % str( e ) )

    # Populate column so that user_id is the id of the user who owns the history_dataset_association (and, up to now, was the only person able to tag the page).
    if c is HistoryDatasetAssociationTagAssociation_table.c.user_id:
        migrate_engine.execute(
            "UPDATE history_dataset_association_tag_association SET user_id=( SELECT history.user_id FROM history, history_dataset_association WHERE history_dataset_association.history_id = history.id AND history_dataset_association.id = history_dataset_association_tag_association.history_dataset_association_id)" )
    if migrate_engine.name != 'sqlite':
        # Create user_id column in page_tag_association table.
        PageTagAssociation_table = Table( "page_tag_association", metadata, autoload=True )
        c = Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
        try:
            c.create( PageTagAssociation_table, index_name='ix_page_tag_association_user_id')
            assert c is PageTagAssociation_table.c.user_id
        except Exception as e:
            # SQLite does not support 'ALTER TABLE ADD FOREIGN KEY', so catch exception if it arises.
            print(str(e))
            log.debug( "Adding user_id column to page_tag_association table failed: %s" % str( e ) )
    else:
        # Create user_id column in page_tag_association table.
        PageTagAssociation_table = Table( "page_tag_association", metadata, autoload=True )
        c = Column( "user_id", Integer )
        try:
            c.create( PageTagAssociation_table )
            assert c is PageTagAssociation_table.c.user_id
        except Exception as e:
            # SQLite does not support 'ALTER TABLE ADD FOREIGN KEY', so catch exception if it arises.
            print(str(e))
            log.debug( "Adding user_id column to page_tag_association table failed: %s" % str( e ) )

    # Populate column so that user_id is the id of the user who owns the page (and, up to now, was the only person able to tag the page).
    if c is PageTagAssociation_table.c.user_id:
        migrate_engine.execute(
            "UPDATE page_tag_association SET user_id=( SELECT user_id FROM page WHERE page_tag_association.page_id = page.id )" )

    # Create stored_workflow_tag_association table.
    try:
        StoredWorkflowTagAssociation_table.create()
    except Exception as e:
        print(str(e))
        log.debug( "Creating stored_workflow_tag_association table failed: %s" % str( e ) )

    # Create workflow_tag_association table.
    try:
        WorkflowTagAssociation_table.create()
    except Exception as e:
        print(str(e))
        log.debug( "Creating workflow_tag_association table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop user_id column from history_tag_association table.
    HistoryTagAssociation_table = Table( "history_tag_association", metadata, autoload=True )
    try:
        HistoryTagAssociation_table.c.user_id.drop()
    except Exception as e:
        print(str(e))
        log.debug( "Dropping column user_id from history_tag_association table failed: %s" % str( e ) )

    # Drop user_id column from history_dataset_association_tag_association table.
    HistoryDatasetAssociationTagAssociation_table = Table( "history_dataset_association_tag_association", metadata, autoload=True )
    try:
        HistoryDatasetAssociationTagAssociation_table.c.user_id.drop()
    except Exception as e:
        print(str(e))
        log.debug( "Dropping column user_id from history_dataset_association_tag_association table failed: %s" % str( e ) )

    # Drop user_id column from page_tag_association table.
    PageTagAssociation_table = Table( "page_tag_association", metadata, autoload=True )
    try:
        PageTagAssociation_table.c.user_id.drop()
    except Exception as e:
        print(str(e))
        log.debug( "Dropping column user_id from page_tag_association table failed: %s" % str( e ) )

    # Drop stored_workflow_tag_association table.
    try:
        StoredWorkflowTagAssociation_table.drop()
    except Exception as e:
        print(str(e))
        log.debug( "Dropping stored_workflow_tag_association table failed: %s" % str( e ) )

    # Drop workflow_tag_association table.
    try:
        WorkflowTagAssociation_table.drop()
    except Exception as e:
        print(str(e))
        log.debug( "Dropping workflow_tag_association table failed: %s" % str( e ) )
