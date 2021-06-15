"""
This script fixes a problem introduced in the previous migration script
0010_hda_display_at_authz_table.py .  MySQL has a name length limit and
thus the index "ix_hdadaa_history_dataset_association_id" has to be
manually created.
"""

import datetime
import logging

from sqlalchemy import MetaData

from galaxy.model.migrate.versions.util import (
    add_index,
    drop_index,
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    if migrate_engine.name == 'mysql':
        add_index('ix_hdadaa_history_dataset_association_id', 'history_dataset_association_display_at_authorization', 'history_dataset_association_id', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    if migrate_engine.name == 'mysql':
        drop_index('ix_hdadaa_history_dataset_association_id', 'history_dataset_association_display_at_authorization', 'history_dataset_association_id', metadata)
