"""
Migration script to rename the sequencer information form type to external service information form
"""

import logging

from sqlalchemy import MetaData

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    current_form_type = 'Sequencer Information Form'
    new_form_type = "External Service Information Form"
    cmd = "update form_definition set type='{}' where type='{}'".format(new_form_type, current_form_type)
    migrate_engine.execute(cmd)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    new_form_type = 'Sequencer Information Form'
    current_form_type = "External Service Information Form"
    cmd = "update form_definition set type='{}' where type='{}'".format(new_form_type, current_form_type)
    migrate_engine.execute(cmd)
