"""Migration script to change repository.type column value from generic to unrestricted."""

import logging
import sys

from sqlalchemy import MetaData

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
    # Update the type column to have the default unrestricted value.
    cmd = "UPDATE repository SET type = 'unrestricted' WHERE type = 'generic'"
    migrate_engine.execute(cmd)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Update the type column to have the default generic value.
    cmd = "UPDATE repository SET type = 'generic' WHERE type = 'unrestricted'"
    migrate_engine.execute(cmd)
