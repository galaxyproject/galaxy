"""
This migration script changes certain values in the history_dataset_association.extension
column, specifically 'qual' is changed to be 'qual454'.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import Index, MetaData, Table

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)

metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    HistoryDatasetAssociation_table = Table("history_dataset_association", metadata, autoload=True)
    # Load existing tables
    metadata.reflect()
    # Add 2 indexes to the galaxy_user table
    i = Index('ix_hda_extension', HistoryDatasetAssociation_table.c.extension)
    try:
        i.create()
    except Exception:
        log.exception("Adding index 'ix_hda_extension' to history_dataset_association table failed.")

    # Set the default data in the galaxy_user table, but only for null values
    cmd = "UPDATE history_dataset_association SET extension = 'qual454' WHERE extension = 'qual' and peek like \'>%%\'"
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Resetting extension qual to qual454 in history_dataset_association failed.")
    cmd = "UPDATE history_dataset_association SET extension = 'qualsolexa' WHERE extension = 'qual' and peek not like \'>%%\'"
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Resetting extension qual to qualsolexa in history_dataset_association failed.")
    # Add 1 index to the history_dataset_association table
    try:
        i.drop()
    except Exception:
        log.exception("Dropping index 'ix_hda_extension' to history_dataset_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
