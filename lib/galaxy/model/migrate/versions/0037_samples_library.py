"""
This migration script removes the library_id & folder_id fields in the 'request' table and
adds the same to the 'sample' table. This also adds a 'datatx' column to request_type table
to store the sequencer login information. Finally, this adds a 'dataset_files' column to
the sample table.
"""
from __future__ import print_function

import datetime
import logging
import sys

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

now = datetime.datetime.utcnow
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
    metadata.reflect()

    # Add the datatx_info column in 'request_type' table
    col = Column("datatx_info", JSONType())
    add_column(col, 'request_type', metadata)

    # Delete the library_id column in 'request' table
    Request_table = Table("request", metadata, autoload=True)
    drop_column('library_id', Request_table)

    # Delete the folder_id column in 'request' table
    drop_column('folder_id', Request_table)

    # Add the dataset_files column in 'sample' table
    Sample_table = Table("sample", metadata, autoload=True)
    col = Column("dataset_files", JSONType())
    add_column(col, Sample_table)

    # Add the library_id column in 'sample' table
    # SQLAlchemy Migrate has a bug when adding a column with both a ForeignKey and a index in SQLite
    if migrate_engine.name != 'sqlite':
        col = Column("library_id", Integer, ForeignKey("library.id"), index=True)
    else:
        col = Column("library_id", Integer, index=True)
    add_column(col, Sample_table, index_name='ix_sample_library_id')

    # Add the library_id column in 'sample' table
    # SQLAlchemy Migrate has a bug when adding a column with both a ForeignKey and a index in SQLite
    if migrate_engine.name != 'sqlite':
        col = Column("folder_id", Integer, ForeignKey("library_folder.id"), index=True)
    else:
        col = Column("folder_id", Integer, index=True)
    add_column(col, Sample_table, index_name='ix_sample_library_folder_id')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    Sample_table = Table("sample", metadata, autoload=True)
    drop_column('folder_id', Sample_table)
    drop_column('library_id', Sample_table)
    drop_column('dataset_files', Sample_table)

    Request_table = Table("request", metadata, autoload=True)
    # SQLAlchemy Migrate has a bug when adding a column with both a ForeignKey and a index in SQLite
    if migrate_engine.name != 'sqlite':
        col = Column('folder_id', Integer, ForeignKey('library_folder.id', name='request_folder_id_fk'), index=True)
    else:
        col = Column('folder_id', Integer, index=True)
    add_column(col, Request_table, index_name='ix_request_folder_id')

    # SQLAlchemy Migrate has a bug when adding a column with both a ForeignKey and a index in SQLite
    if migrate_engine.name != 'sqlite':
        col = Column('library_id', Integer, ForeignKey("library.id"), index=True)
    else:
        col = Column('library_id', Integer, index=True)
    add_column(col, Request_table, index_name='ix_request_library_id')

    drop_column('datatx_info', 'request_type', metadata)
