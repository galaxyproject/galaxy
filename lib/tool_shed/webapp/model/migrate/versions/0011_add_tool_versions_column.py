"""
Migration script to add the tool_versions column to the repository_metadata table.
"""

import datetime
import logging
import sys

from sqlalchemy import (
    Column,
    MetaData,
    Table,
)

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import JSONType

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)

metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    RepositoryMetadata_table = Table("repository_metadata", metadata, autoload=True)
    c = Column("tool_versions", JSONType, nullable=True)
    try:
        # Create
        c.create(RepositoryMetadata_table)
        assert c is RepositoryMetadata_table.c.tool_versions
    except Exception:
        log.exception("Adding tool_versions column to the repository_metadata table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop new_repo_alert column from galaxy_user table.
    RepositoryMetadata_table = Table("repository_metadata", metadata, autoload=True)
    try:
        RepositoryMetadata_table.c.tool_versions.drop()
    except Exception:
        log.exception("Dropping column tool_versions from the repository_metadata table failed.")
