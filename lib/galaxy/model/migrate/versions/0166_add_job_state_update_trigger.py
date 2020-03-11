"""
Migration script to add a trigger to Job table that updates associated datasets
on job update.
"""

from __future__ import print_function

import logging

from sqlalchemy import MetaData

from galaxy.model.triggers import JobStateTrigger

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    trigger = JobStateTrigger(migrate_engine)
    trigger.create()


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    trigger = JobStateTrigger(migrate_engine)
    trigger.drop()
