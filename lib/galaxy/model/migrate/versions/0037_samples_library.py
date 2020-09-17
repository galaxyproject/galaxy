"""
This migration script removes the library_id & folder_id fields in the 'request' table and
adds the same to the 'sample' table. This also adds a 'datatx' column to request_type table
to store the sequencer login information. Finally, this adds a 'dataset_files' column to
the sample table.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
)

from galaxy.model.custom_types import (
    JSONType,
)
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the datatx_info column in 'request_type' table
    col = Column("datatx_info", JSONType())
    add_column(col, 'request_type', metadata)

    # Delete the library_id column in 'request' table
    Request_table = Table("request", metadata, autoload=True)
    # TODO: Dropping a column used in a foreign key fails in MySQL, need to remove the FK first.
    drop_column('library_id', Request_table)

    # Delete the folder_id column in 'request' table
    # TODO: Dropping a column used in a foreign key fails in MySQL, need to remove the FK first.
    drop_column('folder_id', Request_table)

    # Add the dataset_files column in 'sample' table
    Sample_table = Table("sample", metadata, autoload=True)
    col = Column("dataset_files", JSONType())
    add_column(col, Sample_table, metadata)

    # Add the library_id column in 'sample' table
    col = Column("library_id", Integer, ForeignKey("library.id"), index=True)
    add_column(col, Sample_table, metadata, index_name='ix_sample_library_id')

    # Add the library_id column in 'sample' table
    col = Column("folder_id", Integer, ForeignKey("library_folder.id"), index=True)
    add_column(col, Sample_table, metadata, index_name='ix_sample_library_folder_id')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    Sample_table = Table("sample", metadata, autoload=True)
    drop_column('folder_id', Sample_table)
    drop_column('library_id', Sample_table)
    drop_column('dataset_files', Sample_table)

    Request_table = Table("request", metadata, autoload=True)
    col = Column('folder_id', Integer, ForeignKey('library_folder.id'), index=True)
    add_column(col, Request_table, metadata, index_name='ix_request_folder_id')

    col = Column('library_id', Integer, ForeignKey("library.id"), index=True)
    add_column(col, Request_table, metadata, index_name='ix_request_library_id')

    drop_column('datatx_info', 'request_type', metadata)
