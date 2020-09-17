"""
Migration script to add imported column for jobs table.
"""

import logging

from sqlalchemy import Boolean, Column, MetaData, Table

from galaxy.model.migrate.versions.util import add_column, drop_column, engine_false

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create and initialize imported column in job table.
    Jobs_table = Table("job", metadata, autoload=True)
    c = Column("imported", Boolean, default=False, index=True)
    add_column(c, Jobs_table, metadata, index_name="ix_job_imported")
    try:
        migrate_engine.execute("UPDATE job SET imported=%s" % engine_false(migrate_engine))
    except Exception:
        log.exception("Updating column 'imported' of table 'job' failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('imported', 'job', metadata)
