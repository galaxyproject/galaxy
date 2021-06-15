"""
Add support for job destinations to the job table
"""

import logging

from sqlalchemy import Column, MetaData, String, Table

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()
    Job_table = Table("job", metadata, autoload=True)

    c = Column("destination_id", String(255), nullable=True)
    try:
        c.create(Job_table)
        assert c is Job_table.c.destination_id
    except Exception:
        log.exception("Adding column 'destination_id' to job table failed.")

    c = Column("destination_params", JSONType, nullable=True)
    try:
        c.create(Job_table)
        assert c is Job_table.c.destination_params
    except Exception:
        log.exception("Adding column 'destination_params' to job table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()
    Job_table = Table("job", metadata, autoload=True)

    try:
        Job_table.c.destination_params.drop()
    except Exception:
        log.exception("Dropping column 'destination_params' from job table failed.")

    try:
        Job_table.c.destination_id.drop()
    except Exception:
        log.exception("Dropping column 'destination_id' from job table failed.")
