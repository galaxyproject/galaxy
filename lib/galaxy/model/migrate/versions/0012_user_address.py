"""
This script adds a new user_address table that is currently only used with sample requests, where
a user can select from a list of his addresses to associate with the request.  This script also
drops the request.submitted column which was boolean and replaces it with a request.state column
which is a string, allowing for more flexibility with request states.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)
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
    try:
        UserAddress_table.create()
    except Exception:
        log.exception("Creating user_address table failed.")
    # Add 1 column to the request_type table
    try:
        RequestType_table = Table("request_type", metadata, autoload=True)
    except NoSuchTableError:
        RequestType_table = None
        log.debug("Failed loading table request_type")
    if RequestType_table is not None:
        try:
            col = Column("deleted", Boolean, index=True, default=False)
            col.create(RequestType_table, index_name='ix_request_type_deleted')
            assert col is RequestType_table.c.deleted
        except Exception:
            log.exception("Adding column 'deleted' to request_type table failed.")

    # Delete the submitted column
    # This fails for sqlite, so skip the drop -- no conflicts in the future
    try:
        Request_table = Table("request", metadata, autoload=True)
    except NoSuchTableError:
        Request_table = None
        log.debug("Failed loading table request")
    if Request_table is not None:
        # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
        if migrate_engine.name != 'sqlite':
            Request_table.c.submitted.drop()
        col = Column("state", TrimmedString(255), index=True)
        col.create(Request_table, index_name='ix_request_state')
        assert col is Request_table.c.state


def downgrade(migrate_engine):
    pass
