"""Migration script to add the numeric_revision column to the repository metadata table."""

import logging
import sys

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
)

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
    c = Column("numeric_revision", Integer, index=True)
    try:
        # Create
        c.create(RepositoryMetadata_table, index_name="ix_numeric_revision")
        assert c is RepositoryMetadata_table.c.numeric_revision
    except Exception:
        log.exception("Adding numeric_revision column to the repository table failed.")
    # Update the numeric_revision column to have the default undefined value.
    cmd = "UPDATE repository_metadata SET numeric_revision = -1"
    migrate_engine.execute(cmd)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop numeric_revision column from repository table.
    RepositoryMetadata_table = Table("repository_metadata", metadata, autoload=True)
    try:
        RepositoryMetadata_table.c.numeric_revision.drop()
    except Exception:
        log.exception("Dropping column numeric_revision from the repository table failed.")
