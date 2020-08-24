"""
Migration script to add the post_job_action_association table.
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

from galaxy.model.migrate.versions.util import create_table, drop_table

log = logging.getLogger(__name__)
metadata = MetaData()

PostJobActionAssociation_table = Table("post_job_action_association", metadata,
                                       Column("id", Integer, primary_key=True),
                                       Column("post_job_action_id", Integer, ForeignKey("post_job_action.id"), index=True, nullable=False),
                                       Column("job_id", Integer, ForeignKey("job.id"), index=True, nullable=False))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(PostJobActionAssociation_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(PostJobActionAssociation_table)
