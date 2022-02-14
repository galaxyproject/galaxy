"""
Migration script to add the repository_metadata table.
"""

import datetime
import logging
import sys

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
)

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import (
    JSONType,
    TrimmedString,
)

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)

metadata = MetaData()

RepositoryMetadata_table = Table(
    "repository_metadata",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("repository_id", Integer, ForeignKey("repository.id"), index=True),
    Column("changeset_revision", TrimmedString(255), index=True),
    Column("metadata", JSONType, nullable=True),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    # Create repository_metadata table.
    try:
        RepositoryMetadata_table.create()
    except Exception:
        log.exception("Creating repository_metadata table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop repository_metadata table.
    try:
        RepositoryMetadata_table.drop()
    except Exception:
        log.exception("Dropping repository_metadata table failed.")
