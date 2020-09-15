"""
Migration script to add a synopsis column to the library table.
"""

import logging

from sqlalchemy import (
    Column,
    MetaData,
    Table,
    TEXT
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        Library_table = Table("library", metadata, autoload=True)
        c = Column("synopsis", TEXT)
        c.create(Library_table)
        assert c is Library_table.c.synopsis
    except Exception:
        log.exception("Adding column 'synopsis' to 'library' table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        Library_table = Table("library", metadata, autoload=True)
        Library_table.c.synopsis.drop()
    except Exception:
        log.exception("Dropping column 'synopsis' from 'library' table failed")
