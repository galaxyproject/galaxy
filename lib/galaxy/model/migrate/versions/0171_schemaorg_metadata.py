"""
Adds license and creator metadata to workflow.
"""
import datetime
import logging

from sqlalchemy import (
    Column,
    MetaData,
    TEXT,
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column,
)

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Add person metadata in future pass at this.
    # person_metadata_column = Column('person_metadata', JSONType, default=None)
    # add_column(person_metadata_column, 'galaxy_user', metadata)

    creator_metadata_column = Column("creator_metadata", JSONType, default=None)
    add_column(creator_metadata_column, "workflow", metadata)

    license_column = Column("license", TEXT, default=None)
    add_column(license_column, "workflow", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # drop_column('person_metadata', 'galaxy_user', metadata)
    drop_column("creator_metadata", "workflow", metadata)
    drop_column("license", "workflow", metadata)
