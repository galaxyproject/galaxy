"""
Migration script to add status and error_message columns to the tool_dependency table and drop the uninstalled column from the tool_dependency table.
"""

import logging

from sqlalchemy import (
    Boolean,
    Column,
    MetaData,
    Table,
    TEXT
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    ToolDependency_table = Table("tool_dependency", metadata, autoload=True)
    if migrate_engine.name == 'sqlite':
        col = Column("status", TrimmedString(255))
    else:
        col = Column("status", TrimmedString(255), nullable=False)
    add_column(col, ToolDependency_table, metadata)

    col = Column("error_message", TEXT)
    add_column(col, ToolDependency_table, metadata)

    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    # TODO move to alembic.
    if migrate_engine.name != 'sqlite':
        drop_column('uninstalled', ToolDependency_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    ToolDependency_table = Table("tool_dependency", metadata, autoload=True)
    if migrate_engine.name != 'sqlite':
        col = Column("uninstalled", Boolean, default=False)
        add_column(col, ToolDependency_table, metadata)

    drop_column('error_message', ToolDependency_table)
    drop_column('status', ToolDependency_table)
