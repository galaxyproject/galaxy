"""
Migration script to add the downloadable column to the repository_metadata table.
"""

import logging
import sys

from sqlalchemy import (
    Boolean,
    Column,
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
    # Create and initialize imported column in job table.
    RepositoryMetadata_table = Table("repository_metadata", metadata, autoload=True)
    c = Column("downloadable", Boolean, default=True)
    try:
        # Create
        c.create(RepositoryMetadata_table)
        assert c is RepositoryMetadata_table.c.downloadable
        # Initialize.
        if migrate_engine.name == "mysql" or migrate_engine.name == "sqlite":
            default_true = "1"
        elif migrate_engine.name in ["postgresql", "postgres"]:
            default_true = "true"
        migrate_engine.execute(f"UPDATE repository_metadata SET downloadable={default_true}")
    except Exception:
        log.exception("Adding downloadable column to the repository_metadata table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop downloadable column from repository_metadata table.
    RepositoryMetadata_table = Table("repository_metadata", metadata, autoload=True)
    try:
        RepositoryMetadata_table.c.downloadable.drop()
    except Exception:
        log.exception("Dropping column downloadable from the repository_metadata table failed.")
