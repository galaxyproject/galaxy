"""
This script creates a request.folder_id column which is a foreign
key to the library_folder table. This also adds a 'type' and 'layout' column
to the form_definition table.
"""
from __future__ import print_function

import logging

from migrate import ForeignKeyConstraint
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table
)

from galaxy.model.custom_types import (
    JSONType,
    TrimmedString
)
from galaxy.model.migrate.versions.util import (
    add_column,
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create the folder_id column
    Request_table = Table("request", metadata, autoload=True)
    col = Column("folder_id", Integer, index=True)
    add_column(col, Request_table, index_name='ix_request_folder_id')
    LibraryFolder_table = Table("library_folder", metadata, autoload=True)
    # Add 1 foreign key constraint to the library_folder table
    if migrate_engine.name != 'sqlite':
        try:
            cons = ForeignKeyConstraint([Request_table.c.folder_id],
                                        [LibraryFolder_table.c.id],
                                        name='request_folder_id_fk')
            # Create the constraint
            cons.create()
        except Exception:
            log.exception("Adding foreign key constraint 'request_folder_id_fk' to table 'library_folder' failed.")
    # Create the type column in form_definition
    FormDefinition_table = Table("form_definition", metadata, autoload=True)
    col = Column("type", TrimmedString(255), index=True)
    add_column(col, FormDefinition_table, index_name='ix_form_definition_type')
    col = Column("layout", JSONType())
    add_column(col, FormDefinition_table)


def downgrade(migrate_engine):
    pass
