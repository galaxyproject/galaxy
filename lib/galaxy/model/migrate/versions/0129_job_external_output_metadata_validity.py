"""
Migration script to allow invalidation of job external output metadata temp files
"""

import logging

from sqlalchemy import Boolean, Column, MetaData

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    isvalid_column = Column("is_valid", Boolean, default=True)
    add_column(isvalid_column, "job_external_output_metadata", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        drop_column("is_valid", "job_external_output_metadata", metadata)
