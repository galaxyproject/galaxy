"""
Updates timestamp trigger to use FOR EACH STATEMENT instead of FOR EACH ROW to avoid deadlocks.
"""

import logging

from sqlalchemy import MetaData

from galaxy.model.triggers import drop_timestamp_triggers, install_timestamp_triggers

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_timestamp_triggers(migrate_engine)
    install_timestamp_triggers(migrate_engine)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_timestamp_triggers(migrate_engine)
