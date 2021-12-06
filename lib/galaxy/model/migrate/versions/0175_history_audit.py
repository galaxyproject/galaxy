"""
Add history audit table and associated triggers
"""

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, PrimaryKeyConstraint, Table

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)
from galaxy.model.triggers import (
    history_update_time_field as old_triggers,  # rollback to old ones
    update_audit_table as new_triggers,  # install me
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

AuditTable = Table(
    "history_audit",
    metadata,
    Column("history_id", Integer, ForeignKey("history.id"), primary_key=True, nullable=False),
    Column("update_time", DateTime, default=now, primary_key=True, nullable=False),
    PrimaryKeyConstraint(sqlite_on_conflict='IGNORE')
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # create table + index
    AuditTable.drop(migrate_engine, checkfirst=True)
    create_table(AuditTable)

    # populate with update_time from every history
    copy_update_times = """
        INSERT INTO history_audit (history_id, update_time)
        SELECT id, update_time FROM history
    """
    migrate_engine.execute(copy_update_times)

    # drop existing timestamp triggers
    old_triggers.drop_timestamp_triggers(migrate_engine)

    # install new timestamp triggers
    new_triggers.install(migrate_engine)


def downgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # drop existing timestamp triggers
    new_triggers.remove(migrate_engine)

    try:
        # update history.update_time with vals from audit table
        put_em_back = """
            UPDATE history h
            SET update_time = a.max_update_time
            FROM (
                SELECT history_id, max(update_time) as max_update_time
                FROM history_audit
                GROUP BY history_id
            ) a
            WHERE h.id = a.history_id
        """
        migrate_engine.execute(put_em_back)
    except Exception:
        print("Unable to put update_times back")

    # drop audit table
    drop_table(AuditTable)

    # install old timestamp triggers
    old_triggers.install_timestamp_triggers(migrate_engine)
