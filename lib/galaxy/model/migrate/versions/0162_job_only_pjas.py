"""
Migration script to allow null workflow_step for PostJobActions.
This enables using PJAs with individual job executions.
"""

import logging

from sqlalchemy import MetaData

from galaxy.model.migrate.versions.util import alter_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Make workflow_step_id nullable to allow for PJAs to be created for
    # individual jobs.
    alter_column("workflow_step_id", "post_job_action", metadata, nullable=True)


def downgrade(migrate_engine):
    # This is not a reversible migration, because post-migrate we may introduce
    # null values to the column which cannot later be easily 'fixed'.  They
    # should not cause any issue to simply ignore, though -- I don't think
    # there was really a great reason this was non-nullable when I first wrote it.
    pass
