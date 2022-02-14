"""
Migration script to add the skip_tool_test table and add the test_install_error column to the repository_metadata table.
"""

import datetime
import logging
import sys

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    TEXT,
)
from sqlalchemy.exc import NoSuchTableError

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)

now = datetime.datetime.utcnow

metadata = MetaData()

SkipToolTest_table = Table(
    "skip_tool_test",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("repository_metadata_id", Integer, ForeignKey("repository_metadata.id"), index=True),
    Column("initial_changeset_revision", TrimmedString(255), index=True),
    Column("comment", TEXT),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    # Initialize.
    if migrate_engine.name == "mysql" or migrate_engine.name == "sqlite":
        default_false = "0"
    elif migrate_engine.name in ["postgresql", "postgres"]:
        default_false = "false"

    try:
        RepositoryMetadata_table = Table("repository_metadata", metadata, autoload=True)
    except NoSuchTableError:
        RepositoryMetadata_table = None
        log.debug("Failed loading table repository_metadata.")

    if RepositoryMetadata_table is not None:
        # Create the test_install_error column.
        c = Column("test_install_error", Boolean, default=False, index=True)
        try:
            c.create(RepositoryMetadata_table, index_name="ix_repository_metadata_ttie")
            assert c is RepositoryMetadata_table.c.test_install_error
            migrate_engine.execute(f"UPDATE repository_metadata SET test_install_error={default_false}")
        except Exception:
            log.exception("Adding test_install_error column to the repository_metadata table failed.")

    # Create skip_tool_test table.
    try:
        SkipToolTest_table.create()
    except Exception:
        log.exception("Creating the skip_tool_test table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the skip_tool_test table.
    try:
        SkipToolTest_table.drop()
    except Exception:
        log.exception("Dropping the skip_tool_test table failed.")

    # Drop test_install_error column from the repository_metadata table.
    RepositoryMetadata_table = Table("repository_metadata", metadata, autoload=True)
    try:
        RepositoryMetadata_table.c.test_install_error.drop()
    except Exception:
        log.exception("Dropping column test_install_error from the repository_metadata table failed.")
