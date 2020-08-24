"""
Migration script to create column and table for importing histories from
file archives.
"""

import logging

from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, Table, TEXT

from galaxy.model.migrate.versions.util import engine_false

log = logging.getLogger(__name__)
metadata = MetaData()

# Columns to add.

importing_col = Column("importing", Boolean, index=True, default=False)
ldda_parent_col = Column("ldda_parent_id", Integer, ForeignKey("library_dataset_dataset_association.id"), index=True)

# Table to add.

JobImportHistoryArchive_table = Table("job_import_history_archive", metadata,
                                      Column("id", Integer, primary_key=True),
                                      Column("job_id", Integer, ForeignKey("job.id"), index=True),
                                      Column("history_id", Integer, ForeignKey("history.id"), index=True),
                                      Column("archive_dir", TEXT))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add column to history table and initialize.
    try:
        History_table = Table("history", metadata, autoload=True)
        importing_col.create(History_table, index_name="ix_history_importing")
        assert importing_col is History_table.c.importing

        # Initialize column to false.
        migrate_engine.execute("UPDATE history SET importing=%s" % engine_false(migrate_engine))
    except Exception:
        log.exception("Adding column 'importing' to history table failed.")

    # Create job_import_history_archive table.
    try:
        JobImportHistoryArchive_table.create()
    except Exception:
        log.exception("Creating job_import_history_archive table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop 'importing' column from history table.
    try:
        History_table = Table("history", metadata, autoload=True)
        importing_col = History_table.c.importing
        importing_col.drop()
    except Exception:
        log.exception("Dropping column 'importing' from history table failed.")

    # Drop job_import_history_archive table.
    try:
        JobImportHistoryArchive_table.drop()
    except Exception:
        log.exception("Dropping job_import_history_archive table failed.")
