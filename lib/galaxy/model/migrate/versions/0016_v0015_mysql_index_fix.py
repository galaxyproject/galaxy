"""
This script fixes a problem introduced in 0015_tagging.py. MySQL has a name length
limit and thus the index "ix_hda_ta_history_dataset_association_id" has to be
manually created.
"""
from __future__ import print_function

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

    add_index('ix_hda_ta_history_dataset_association_id', 'history_dataset_association_tag_association', 'history_dataset_association_id', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_index('ix_hda_ta_history_dataset_association_id', 'history_dataset_association_tag_association', 'history_dataset_association_id', metadata)
