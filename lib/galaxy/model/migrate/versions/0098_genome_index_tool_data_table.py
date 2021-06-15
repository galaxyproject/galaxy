"""
Migration script to create the genome_index_tool_data table.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

GenomeIndexToolData_table = Table("genome_index_tool_data", metadata,
                                  Column("id", Integer, primary_key=True),
                                  Column("job_id", Integer, ForeignKey("job.id"), index=True),
                                  Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
                                  Column("deferred_job_id", Integer, ForeignKey("deferred_job.id"), index=True),
                                  Column("transfer_job_id", Integer, ForeignKey("transfer_job.id"), index=True),
                                  Column("fasta_path", String(255)),
                                  Column("created_time", DateTime, default=now),
                                  Column("modified_time", DateTime, default=now, onupdate=now),
                                  Column("indexer", String(64)),
                                  Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(GenomeIndexToolData_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(GenomeIndexToolData_table)
