"""
This script adds 3 indexes to table columns: library_folder.name,
library_dataset.name, library_dataset_dataset_association.name.
"""

import logging

from sqlalchemy import MetaData

from galaxy.model.migrate.versions.util import (
    add_index,
    drop_index
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    add_index('ix_library_folder_name', 'library_folder', 'name', metadata)
    add_index('ix_library_dataset_dataset_association_name', 'library_dataset_dataset_association', 'name', metadata)
    add_index('ix_library_dataset_name', 'library_dataset', 'name', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_index('ix_library_dataset_name', 'library_dataset', 'name', metadata)
    drop_index('ix_library_dataset_dataset_association_name', 'library_dataset_dataset_association', 'name', metadata)
    drop_index('ix_library_folder_name', 'library_folder', 'name', metadata)
