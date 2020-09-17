"""
This script creates a request.folder_id column which is a foreign
key to the library_folder table. This also adds a 'type' and 'layout' column
to the form_definition table.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
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
    col = Column("folder_id", Integer, ForeignKey('library_folder.id'), index=True)
    add_column(col, 'request', metadata, index_name='ix_request_folder_id')
    # Create the type column in form_definition
    FormDefinition_table = Table("form_definition", metadata, autoload=True)
    col = Column("type", TrimmedString(255), index=True)
    add_column(col, FormDefinition_table, metadata, index_name='ix_form_definition_type')
    col = Column("layout", JSONType())
    add_column(col, FormDefinition_table, metadata)


def downgrade(migrate_engine):
    pass
