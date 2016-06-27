"""
Migration script to create tables for handling post-job actions.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import JSONType

logging.basicConfig( level=logging.DEBUG )
log = logging.getLogger( __name__ )
now = datetime.datetime.utcnow
metadata = MetaData()

PostJobAction_table = Table("post_job_action", metadata,
                            Column("id", Integer, primary_key=True),
                            Column("workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True, nullable=False),
                            Column("action_type", String(255), nullable=False),
                            Column("output_name", String(255), nullable=True),
                            Column("action_arguments", JSONType, nullable=True))

# PostJobActionAssociation_table = Table("post_job_action_association", metadata,
#     Column("id", Integer, primary_key=True),
#     Column("post_job_action_id", Integer, ForeignKey("post_job_action.id"), index=True, nullable=False),
#     Column("job_id", Integer, ForeignKey("job.id"), index=True, nullable=False))

tables = [PostJobAction_table]  # , PostJobActionAssociation_table]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    for table in tables:
        try:
            table.create()
        except:
            log.warning( "Failed to create table '%s', ignoring (might result in wrong schema)" % table.name )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    for table in tables:
        table.drop()
