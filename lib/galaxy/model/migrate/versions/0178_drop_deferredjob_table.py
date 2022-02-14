"""
Drop unused DeferredJob table and foreign key column on genome_index_tool_data.
"""

import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    TEXT,
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table,
)
from galaxy.model.orm.now import now

log = logging.getLogger(__name__)
metadata = MetaData()

DeferredJob_table = Table(
    "deferred_job",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("state", String(64), index=True),
    Column("plugin", String(128), index=True),
    Column("params", JSONType),
    Column("info", TEXT),
)

deferred_job_id = Column("deferred_job_id", Integer, ForeignKey("deferred_job.id"), index=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        drop_column(deferred_job_id.name, "genome_index_tool_data", metadata)
        drop_table(DeferredJob_table)
    except Exception:
        log.exception("Dropping deferred_job table failed")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        create_table(DeferredJob_table)
        add_column(
            deferred_job_id, "genome_index_tool_data", metadata, index_name="ix_genome_index_tool_data_deferred_job_id"
        )
    except Exception:
        log.exception("Creating deferred_job table failed")
