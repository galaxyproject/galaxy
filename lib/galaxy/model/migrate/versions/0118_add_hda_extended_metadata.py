"""
Add link from history_dataset_association to the extended_metadata table
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

log = logging.getLogger(__name__)
metadata = MetaData()
extended_metadata_hda_col = Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), nullable=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        hda_table = Table("history_dataset_association", metadata, autoload=True)
        extended_metadata_hda_col.create(hda_table)
        assert extended_metadata_hda_col is hda_table.c.extended_metadata_id
    except Exception:
        log.exception("Adding column 'extended_metadata_id' to history_dataset_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the HDA table's extended metadata ID column.
    try:
        hda_table = Table("history_dataset_association", metadata, autoload=True)
        extended_metadata_id = hda_table.c.extended_metadata_id
        extended_metadata_id.drop()
    except Exception:
        log.exception("Dropping 'extended_metadata_id' column from history_dataset_association table failed.")
