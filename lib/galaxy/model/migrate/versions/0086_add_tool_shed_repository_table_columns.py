"""
Migration script to add the metadata, update_available and includes_datatypes columns to the tool_shed_repository table.
"""

import logging

from sqlalchemy import (
    Boolean,
    Column,
    MetaData,
    Table
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column,
    engine_false
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    ToolShedRepository_table = Table("tool_shed_repository", metadata, autoload=True)
    c = Column("metadata", JSONType(), nullable=True)
    add_column(c, ToolShedRepository_table, metadata)
    c = Column("includes_datatypes", Boolean, index=True, default=False)
    add_column(c, ToolShedRepository_table, metadata, index_name="ix_tool_shed_repository_includes_datatypes")
    try:
        migrate_engine.execute("UPDATE tool_shed_repository SET includes_datatypes=%s" % engine_false(migrate_engine))
    except Exception:
        log.exception("Updating column 'includes_datatypes' of table 'tool_shed_repository' failed.")
    c = Column("update_available", Boolean, default=False)
    add_column(c, ToolShedRepository_table, metadata)
    try:
        migrate_engine.execute("UPDATE tool_shed_repository SET update_available=%s" % engine_false(migrate_engine))
    except Exception:
        log.exception("Updating column 'update_available' of table 'tool_shed_repository' failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    ToolShedRepository_table = Table("tool_shed_repository", metadata, autoload=True)
    drop_column('metadata', ToolShedRepository_table)
    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        drop_column('includes_datatypes', ToolShedRepository_table)
        drop_column('update_available', ToolShedRepository_table)
