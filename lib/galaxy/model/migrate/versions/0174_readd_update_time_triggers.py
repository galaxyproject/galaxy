"""
Re-add triggers to update history.update_time when contents are changed.
"""

import logging

from sqlalchemy import MetaData

from galaxy.model.migrate.triggers.history_update_time_field import (
    drop_timestamp_triggers,
    install_timestamp_triggers,
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    install_timestamp_triggers(migrate_engine)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_timestamp_triggers(migrate_engine)
