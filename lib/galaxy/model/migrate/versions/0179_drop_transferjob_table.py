"""
Drop unused TransferJob table and foreign key column on genome_index_tool_data.
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

TransferJob_table = Table(
    "transfer_job",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("state", String(64), index=True),
    Column("path", String(1024)),
    Column("params", JSONType),
    Column("pid", Integer),
    Column("socket", Integer),
)

transfer_job_id = Column("transfer_job_id", Integer, ForeignKey("transfer_job.id"), index=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        drop_column(transfer_job_id.name, "genome_index_tool_data", metadata)
        drop_table(TransferJob_table)
    except Exception:
        log.exception("Dropping transfer_job table failed")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        create_table(TransferJob_table)
        add_column(
            transfer_job_id, "genome_index_tool_data", metadata, index_name="ix_genome_index_tool_data_transfer_job_id"
        )
    except Exception:
        log.exception("Creating transfer_job table failed")
