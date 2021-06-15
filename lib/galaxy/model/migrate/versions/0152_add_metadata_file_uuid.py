"""
Adds `uuid` column to MetadataFile table.
"""


import logging

from sqlalchemy import (
    Column,
    MetaData
)

from galaxy.model.custom_types import UUIDType
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    uuid_column = Column('uuid', UUIDType())
    add_column(uuid_column, 'metadata_file', metadata)


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('uuid', 'metadata_file', metadata)
