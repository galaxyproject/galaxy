"""
Migration script to add 'purged' column to the library_dataset table.
"""

import logging

from sqlalchemy import Boolean, Column, MetaData

from galaxy.model.migrate.versions.util import add_column, drop_column, engine_false, engine_true

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    c = Column('purged', Boolean, index=True, default=False)
    add_column(c, 'library_dataset', metadata, index_name='ix_library_dataset_purged')
    # Update the purged flag to the default False
    cmd = "UPDATE library_dataset SET purged = %s;" % engine_false(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Setting default data for library_dataset.purged column failed.")

    # Update the purged flag for those LibaryDatasets whose purged flag should be True.  This happens
    # when the LibraryDataset has no active LibraryDatasetDatasetAssociations.
    cmd = "SELECT * FROM library_dataset WHERE deleted = %s;" % engine_true(migrate_engine)
    deleted_lds = migrate_engine.execute(cmd).fetchall()
    for row in deleted_lds:
        cmd = "SELECT * FROM library_dataset_dataset_association WHERE library_dataset_id = %d AND library_dataset_dataset_association.deleted = %s;" % (int(row.id), engine_false(migrate_engine))
        active_lddas = migrate_engine.execute(cmd).fetchall()
        if not active_lddas:
            print("Updating purged column to True for LibraryDataset id : ", int(row.id))
            cmd = "UPDATE library_dataset SET purged = %s WHERE id = %d;" % (engine_true(migrate_engine), int(row.id))
            migrate_engine.execute(cmd)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        drop_column('purged', 'library_dataset', metadata)
