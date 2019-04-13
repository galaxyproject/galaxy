"""
This script fixes a problem introduced in the previous migration script
0010_hda_display_at_atuhz_table.py .  MySQL has a name length limit and
thus the index "ix_hdadaa_history_dataset_association_id" has to be
manually created.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import MetaData

from galaxy.model.migrate.versions.util import (
    add_index,
    drop_index,
)

now = datetime.datetime.utcnow
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

    if migrate_engine.name == 'mysql':
        add_index('ix_hdadaa_history_dataset_association_id', 'history_dataset_association_display_at_authorization', 'history_dataset_association_id', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    if migrate_engine.name == 'mysql':
        drop_index('ix_hdadaa_history_dataset_association_id', 'history_dataset_association_display_at_authorization', 'history_dataset_association_id', metadata)
