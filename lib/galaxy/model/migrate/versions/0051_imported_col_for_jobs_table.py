"""
Migration script to add imported column for jobs table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, MetaData, Table

log = logging.getLogger(__name__)
metadata = MetaData()


def engine_false(migrate_engine):
    if migrate_engine.name in ['postgres', 'postgresql']:
        return "FALSE"
    elif migrate_engine.name in ['mysql', 'sqlite']:
        return 0
    else:
        raise Exception('Unknown database type: %s' % migrate_engine.name)


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create and initialize imported column in job table.
    Jobs_table = Table("job", metadata, autoload=True)
    c = Column("imported", Boolean, default=False, index=True)
    try:
        # Create
        c.create(Jobs_table, index_name="ix_job_imported")
        assert c is Jobs_table.c.imported

        migrate_engine.execute("UPDATE job SET imported=%s" % engine_false(migrate_engine))
    except Exception:
        log.exception("Adding imported column to job table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop imported column from job table.
    Jobs_table = Table("job", metadata, autoload=True)
    try:
        Jobs_table.c.imported.drop()
    except Exception:
        log.exception("Dropping column imported from job table failed.")
