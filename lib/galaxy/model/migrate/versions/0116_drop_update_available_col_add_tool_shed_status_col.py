"""
Migration script to drop the update_available Boolean column and replace it with the tool_shed_status JSONType column in the tool_shed_repository table.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import Boolean, Column, MetaData, Table
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import add_column, drop_column, engine_false

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
        ToolShedRepository_table = Table("tool_shed_repository", metadata, autoload=True)
    except NoSuchTableError:
        ToolShedRepository_table = None
        log.debug("Failed loading table tool_shed_repository")
    if ToolShedRepository_table is not None:
        # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
        if migrate_engine.name != 'sqlite':
            drop_column('update_available', ToolShedRepository_table)
        c = Column("tool_shed_status", JSONType, nullable=True)
        add_column(c, ToolShedRepository_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        ToolShedRepository_table = Table("tool_shed_repository", metadata, autoload=True)
    except NoSuchTableError:
        ToolShedRepository_table = None
        log.debug("Failed loading table tool_shed_repository")
    if ToolShedRepository_table is not None:
        # For some unknown reason it is no longer possible to drop a column in a migration script if using the sqlite database.
        if migrate_engine.name != 'sqlite':
            drop_column('tool_shed_status', ToolShedRepository_table)
            c = Column("update_available", Boolean, default=False)
            add_column(c, ToolShedRepository_table)
            try:
                migrate_engine.execute("UPDATE tool_shed_repository SET update_available=%s" % engine_false(migrate_engine))
            except Exception:
                log.exception("Updating column 'update_available' of table 'tool_shed_repository' failed.")
