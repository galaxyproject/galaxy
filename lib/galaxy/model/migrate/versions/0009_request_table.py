"""
This migration script adds a new column to 2 tables:
1) a new boolean type column named 'submitted' to the 'request' table
2) a new string type column named 'bar_code' to the 'sample' table
"""

import logging

from sqlalchemy import (
    Boolean,
    Column,
    MetaData
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    col = Column('submitted', Boolean, default=False)
    add_column(col, 'request', metadata)

    col = Column("bar_code", TrimmedString(255), index=True)
    add_column(col, 'sample', metadata, index_name='ix_sample_bar_code')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('bar_code', 'sample', metadata)
    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        drop_column('submitted', 'request', metadata)
