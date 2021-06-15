"""
This script adds the filename_override_metadata column to the JobExternalOutputMetadata table,
allowing existing metadata files to be written when using external metadata and a cluster
set up with read-only access to database/files
"""

import logging

from sqlalchemy import (
    Column,
    MetaData,
    String,
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    col = Column("filename_override_metadata", String(255))
    add_column(col, 'job_external_output_metadata', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('filename_override_metadata', 'job_external_output_metadata', metadata)
