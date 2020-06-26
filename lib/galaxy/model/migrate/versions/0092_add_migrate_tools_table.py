"""
Migration script to create the migrate_tools table.
"""

import logging

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    TEXT
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

MigrateTools_table = Table("migrate_tools", metadata,
                           Column("repository_id", TrimmedString(255)),
                           Column("repository_path", TEXT),
                           Column("version", Integer))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(MigrateTools_table)
    try:
        cmd = "INSERT INTO migrate_tools VALUES ('GalaxyTools', 'lib/galaxy/tool_shed/migrate', %d)" % 1
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Inserting into table 'migrate_tools' failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(MigrateTools_table)
