"""
Migration script to drop the installed_changeset_revision column from the tool_dependency table.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import MetaData, Table
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.migrate.versions.util import drop_column

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
    try:
        ToolDependency_table = Table("tool_dependency", metadata, autoload=True)
    except NoSuchTableError:
        ToolDependency_table = None
        log.debug("Failed loading table tool_dependency")
    if ToolDependency_table is not None:
        drop_column('installed_changeset_revision', ToolDependency_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
