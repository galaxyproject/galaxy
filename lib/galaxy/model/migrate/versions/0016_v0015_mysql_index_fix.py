"""
This script was used to fix a problem introduced in 0015_tagging.py. MySQL has a
name length limit and thus the index "ix_hda_ta_history_dataset_association_id"
had to be manually created.

This is now fixed in SQLAlchemy Migrate.
"""

import logging

from sqlalchemy import (
    MetaData,
    Table
)

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

    HistoryDatasetAssociationTagAssociation_table = Table('history_dataset_association_tag_association', metadata, autoload=True)
    if not any([_.name for _ in index.columns] == ['history_dataset_association_id'] for index in HistoryDatasetAssociationTagAssociation_table.indexes):
        add_index('ix_hda_ta_history_dataset_association_id', HistoryDatasetAssociationTagAssociation_table, 'history_dataset_association_id')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_index('ix_hda_ta_history_dataset_association_id', 'history_dataset_association_tag_association', 'history_dataset_association_id', metadata)
