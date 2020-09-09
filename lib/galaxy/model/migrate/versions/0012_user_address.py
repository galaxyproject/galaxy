"""
This script adds a new user_address table that is currently only used with sample requests, where
a user can select from a list of his addresses to associate with the request.  This script also
drops the request.submitted column which was boolean and replaces it with a request.state column
which is a string, allowing for more flexibility with request states.
"""

import datetime
import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    TEXT
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

UserAddress_table = Table("user_address", metadata,
                          Column("id", Integer, primary_key=True),
                          Column("create_time", DateTime, default=now),
                          Column("update_time", DateTime, default=now, onupdate=now),
                          Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                          Column("desc", TEXT),
                          Column("name", TrimmedString(255), nullable=False),
                          Column("institution", TrimmedString(255)),
                          Column("address", TrimmedString(255), nullable=False),
                          Column("city", TrimmedString(255), nullable=False),
                          Column("state", TrimmedString(255), nullable=False),
                          Column("postal_code", TrimmedString(255), nullable=False),
                          Column("country", TrimmedString(255), nullable=False),
                          Column("phone", TrimmedString(255)),
                          Column("deleted", Boolean, index=True, default=False),
                          Column("purged", Boolean, index=True, default=False))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add all of the new tables above
    create_table(UserAddress_table)
    # Add 1 column to the request_type table
    col = Column("deleted", Boolean, index=True, default=False)
    add_column(col, 'request_type', metadata, index_name='ix_request_type_deleted')

    # Delete the submitted column
    # This fails for sqlite, so skip the drop -- no conflicts in the future
    Request_table = Table("request", metadata, autoload=True)
    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        drop_column('submitted', Request_table)
    col = Column("state", TrimmedString(255), index=True)
    add_column(col, Request_table, metadata, index_name='ix_request_state')


def downgrade(migrate_engine):
    pass
