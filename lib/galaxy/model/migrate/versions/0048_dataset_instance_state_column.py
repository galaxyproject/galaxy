"""
Add a state column to the history_dataset_association and library_dataset_dataset_association table.
"""

import logging

from sqlalchemy import (
    Column,
    MetaData,
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()

DATASET_INSTANCE_TABLE_NAMES = ['history_dataset_association', 'library_dataset_dataset_association']


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table_name in DATASET_INSTANCE_TABLE_NAMES:
        col = Column("state", TrimmedString(64), index=True, nullable=True)
        index_name = "ix_%s_state" % table_name
        add_column(col, table_name, metadata, index_name=index_name)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table_name in DATASET_INSTANCE_TABLE_NAMES:
        drop_column('state', table_name, metadata)
