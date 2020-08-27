"""
This migration script adds the history_dataset_association_display_at_authorization table,
which allows 'private' datasets to be displayed at external sites without making them public.

If using mysql, this script will display the following error, which is corrected in the next
migration script:
history_dataset_association_display_at_authorization table failed:  (OperationalError)
(1059, "Identifier name  'ix_history_dataset_association_display_at_authorization_update_time'
is too long
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.custom_types import TrimmedString

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

HistoryDatasetAssociationDisplayAtAuthorization_table = Table("history_dataset_association_display_at_authorization", metadata,
                                                              Column("id", Integer, primary_key=True),
                                                              Column("create_time", DateTime, default=now),
                                                              Column("update_time", DateTime, index=True, default=now, onupdate=now),
                                                              Column("history_dataset_association_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
                                                              Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                              Column("site", TrimmedString(255)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        HistoryDatasetAssociationDisplayAtAuthorization_table.create()
    except Exception:
        log.exception("Creating history_dataset_association_display_at_authorization table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    # Load existing tables
    metadata.reflect()
    try:
        HistoryDatasetAssociationDisplayAtAuthorization_table.drop()
    except Exception:
        log.exception("Dropping history_dataset_association_display_at_authorization table failed.")
