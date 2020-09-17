"""
Migration script to add necessary columns for distinguishing between viewing/importing and publishing histories, \
workflows, and pages. Script adds published column to histories and workflows and importable column to pages.
"""

import logging

from sqlalchemy import Boolean, Column, Index, MetaData, Table

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create published column in history table.
    History_table = Table("history", metadata, autoload=True)
    c = Column("published", Boolean, index=True)
    add_column(c, History_table, metadata, index_name='ix_history_published')
    if migrate_engine.name != 'sqlite':
        # Create index for published column in history table.
        try:
            i = Index("ix_history_published", History_table.c.published)
            i.create()
        except Exception:
            # Mysql doesn't have a named index, but alter should work
            History_table.c.published.alter(unique=False)

    # Create published column in stored workflows table.
    StoredWorkflow_table = Table("stored_workflow", metadata, autoload=True)
    c = Column("published", Boolean, index=True)
    add_column(c, StoredWorkflow_table, metadata, index_name='ix_stored_workflow_published')
    if migrate_engine.name != 'sqlite':
        # Create index for published column in stored workflows table.
        try:
            i = Index("ix_stored_workflow_published", StoredWorkflow_table.c.published)
            i.create()
        except Exception:
            # Mysql doesn't have a named index, but alter should work
            StoredWorkflow_table.c.published.alter(unique=False)

    # Create importable column in page table.
    Page_table = Table("page", metadata, autoload=True)
    c = Column("importable", Boolean, index=True)
    add_column(c, Page_table, metadata, index_name='ix_page_importable')
    if migrate_engine.name != 'sqlite':
        # Create index for importable column in page table.
        try:
            i = Index("ix_page_importable", Page_table.c.importable)
            i.create()
        except Exception:
            # Mysql doesn't have a named index, but alter should work
            Page_table.c.importable.alter(unique=False)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('published', 'history', metadata)
    drop_column('published', 'stored_workflow', metadata)
    drop_column('importable', 'page', metadata)
