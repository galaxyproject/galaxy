"""
Migration script to add the post_job_action_association table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

log = logging.getLogger(__name__)
metadata = MetaData()

PostJobActionAssociation_table = Table("post_job_action_association", metadata,
                                       Column("id", Integer, primary_key=True),
                                       Column("post_job_action_id", Integer, ForeignKey("post_job_action.id"), index=True, nullable=False),
                                       Column("job_id", Integer, ForeignKey("job.id"), index=True, nullable=False))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        PostJobActionAssociation_table.create()
    except Exception:
        log.exception("Creating PostJobActionAssociation table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    # Load existing tables
    metadata.reflect()
    try:
        PostJobActionAssociation_table.drop()
    except Exception:
        log.exception("Dropping PostJobActionAssociation table failed.")
