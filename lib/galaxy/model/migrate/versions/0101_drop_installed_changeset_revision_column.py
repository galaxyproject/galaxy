"""
Migration script to drop the installed_changeset_revision column from the tool_dependency table.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import (
    Column,
    MetaData
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

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

    drop_column('installed_changeset_revision', 'tool_dependency', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    c = Column("installed_changeset_revision", TrimmedString(255))
    add_column(c, "tool_dependency", metadata)
