"""
This migration script creates the new history_user_share_association table, and adds
a new boolean type column to the history table.  This provides support for sharing
histories in the same way that workflows are shared.
"""

import logging

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

HistoryUserShareAssociation_table = Table("history_user_share_association", metadata,
                                          Column("id", Integer, primary_key=True),
                                          Column("history_id", Integer, ForeignKey("history.id"), index=True),
                                          Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(HistoryUserShareAssociation_table)
    col = Column('importable', Boolean, index=True, default=False)
    add_column(col, 'history', metadata, index_name='ix_history_importable')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('importable', 'history', metadata)
    drop_table(HistoryUserShareAssociation_table)
