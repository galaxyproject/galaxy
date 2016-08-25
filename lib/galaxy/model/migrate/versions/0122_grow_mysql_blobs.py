"""
Migration script to grow MySQL blobs.
"""
from __future__ import print_function

from sqlalchemy import MetaData

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

BLOB_COLUMNS = [
    ("deferred_job", "params"),
    ("extended_metadata", "data"),
    ("form_definition", "fields"),
    ("form_definition", "layout"),
    ("form_values", "content"),
    ("history_dataset_association", "metadata"),
    ("job", "destination_params"),
    ("library_dataset_dataset_association", "metadata"),
    ("post_job_action", "action_arguments"),
    ("request", "notification"),
    ("sample", "workflow"),
    ("transfer_job", "params"),
    ("workflow_step", "tool_inputs"),
    ("workflow_step", "tool_errors"),
    ("workflow_step", "position"),
    ("workflow_step", "config"),
    ("tool_shed_repository", "metadata"),
    ("tool_shed_repository", "tool_shed_status"),
]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    if migrate_engine.name != "mysql":
        return

    for (table, column) in BLOB_COLUMNS:
        cmd = "ALTER TABLE %s MODIFY COLUMN %s MEDIUMBLOB;" % (table, column)
        try:
            migrate_engine.execute( cmd )
        except Exception as e:
            print("Failed to grow column %s.%s" % (table, column))
            print(str( e ))


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Ignoring..., changed the datatype so no guarantee these columns weren't
    # MEDIUMBLOBs before.
