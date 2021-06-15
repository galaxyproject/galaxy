"""
Migration script to add 'workflow' and 'history' columns for a sample.
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    Sample_table = Table("sample", metadata, autoload=True)
    c1 = Column("workflow", JSONType, nullable=True)
    add_column(c1, Sample_table, metadata)

    c2 = Column("history_id", Integer, ForeignKey("history.id"), nullable=True)
    add_column(c2, Sample_table, metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    Sample_table = Table("sample", metadata, autoload=True)
    drop_column('workflow', Sample_table)
    drop_column('history_id', Sample_table)
