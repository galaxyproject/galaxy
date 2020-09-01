"""
Migration script to add a trigger to job_to_output_dataset table
that adds job_id to associated output datasets on job insert.
"""

from __future__ import print_function

import logging

from sqlalchemy import MetaData

from galaxy.model.triggers import DatasetJobTrigger

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    trigger = DatasetJobTrigger(migrate_engine)
    trigger.create()


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    trigger = DatasetJobTrigger(migrate_engine)
    trigger.drop()
