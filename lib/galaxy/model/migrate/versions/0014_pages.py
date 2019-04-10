"""
Migration script to add support for "Pages".
  1) Creates Page and PageRevision tables
  2) Adds username column to User table
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, MetaData, String, Table, TEXT

from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table
)

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

Page_table = Table("page", metadata,
                   Column("id", Integer, primary_key=True),
                   Column("create_time", DateTime, default=now),
                   Column("update_time", DateTime, default=now, onupdate=now),
                   Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True, nullable=False),
                   Column("latest_revision_id", Integer,
                          ForeignKey("page_revision.id", use_alter=True, name='page_latest_revision_id_fk'), index=True),
                   Column("title", TEXT),
                   Column("slug", TEXT, unique=True, index=True))

PageRevision_table = Table("page_revision", metadata,
                           Column("id", Integer, primary_key=True),
                           Column("create_time", DateTime, default=now),
                           Column("update_time", DateTime, default=now, onupdate=now),
                           Column("page_id", Integer, ForeignKey("page.id"), index=True, nullable=False),
                           Column("title", TEXT),
                           Column("content", TEXT))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
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
            i = Index("ix_page_slug", Page_table.c.slug, mysql_length=200)
            i.create()
    except Exception:
        log.exception("Could not create page table")
    create_table(PageRevision_table)

    col = Column('username', String(255), index=True, unique=True, default=False)
    add_column(col, 'galaxy_user', metadata, index_name='ix_galaxy_user_username', unique_name='username')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('username', 'galaxy_user', metadata)
    drop_table(PageRevision_table)
    drop_table(Page_table)
