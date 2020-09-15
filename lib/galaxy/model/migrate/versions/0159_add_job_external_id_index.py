"""
Add index for job runner external ID.
"""

import logging

from sqlalchemy import MetaData

from galaxy.model.migrate.versions.util import (
    add_index,
    drop_index
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    add_index('ix_job_job_runner_external_id', 'job', 'job_runner_external_id', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_index('ix_job_job_runner_external_id', 'job', 'job_runner_external_id', metadata)
