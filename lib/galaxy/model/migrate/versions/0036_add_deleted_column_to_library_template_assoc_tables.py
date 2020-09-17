"""
Migration script to add a deleted column to the following tables:
library_info_association, library_folder_info_association, library_dataset_dataset_info_association.
"""

import logging

from sqlalchemy import Boolean, Column, MetaData, Table

from galaxy.model.migrate.versions.util import engine_false

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        LibraryInfoAssociation_table = Table("library_info_association", metadata, autoload=True)
        c = Column("deleted", Boolean, index=True, default=False)
        c.create(LibraryInfoAssociation_table, index_name='ix_library_info_association_deleted')
        assert c is LibraryInfoAssociation_table.c.deleted
    except Exception:
        log.exception("Adding column 'deleted' to 'library_info_association' table failed.")
    cmd = "UPDATE library_info_association SET deleted = %s" % engine_false(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("deleted to false in library_info_association failed.")
    try:
        LibraryFolderInfoAssociation_table = Table("library_folder_info_association", metadata, autoload=True)
        c = Column("deleted", Boolean, index=True, default=False)
        c.create(LibraryFolderInfoAssociation_table, index_name='ix_library_folder_info_association_deleted')
        assert c is LibraryFolderInfoAssociation_table.c.deleted
    except Exception:
        log.exception("Adding column 'deleted' to 'library_folder_info_association' table failed.")
    cmd = "UPDATE library_folder_info_association SET deleted = %s" % engine_false(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("deleted to false in library_folder_info_association failed.")
    try:
        LibraryDatasetDatasetInfoAssociation_table = Table("library_dataset_dataset_info_association", metadata, autoload=True)
        c = Column("deleted", Boolean, index=True, default=False)
        c.create(LibraryDatasetDatasetInfoAssociation_table, index_name='ix_library_dataset_dataset_info_association_deleted')
        assert c is LibraryDatasetDatasetInfoAssociation_table.c.deleted
    except Exception:
        log.exception("Adding column 'deleted' to 'library_dataset_dataset_info_association' table failed.")
    cmd = "UPDATE library_dataset_dataset_info_association SET deleted = %s" % engine_false(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("deleted to false in library_dataset_dataset_info_association failed.")


def downgrade(migrate_engine):
    pass
