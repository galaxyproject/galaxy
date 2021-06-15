"""
This migration script adds the request_event table and
removes the state field in the request table
"""

import datetime
import logging

from sqlalchemy import (
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
    create_table,
    drop_column,
    localtimestamp,
    nextval
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

RequestEvent_table = Table('request_event', metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("request_id", Integer, ForeignKey("request.id"), index=True),
    Column("state", TrimmedString(255), index=True),
    Column("comment", TEXT))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(RequestEvent_table)
    # move the current state of all existing requests to the request_event table
    cmd = \
        "INSERT INTO request_event " + \
        "SELECT %s AS id," + \
        "%s AS create_time," + \
        "%s AS update_time," + \
        "request.id AS request_id," + \
        "request.state AS state," + \
        "'%s' AS comment " + \
        "FROM request;"
    cmd = cmd % (nextval(migrate_engine, 'request_event'), localtimestamp(migrate_engine), localtimestamp(migrate_engine), 'Imported from request table')
    migrate_engine.execute(cmd)

    drop_column('state', 'request', metadata)


def downgrade(migrate_engine):
    pass
