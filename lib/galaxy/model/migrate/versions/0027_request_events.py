"""
This migration script adds the request_event table and
removes the state field in the request table
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import localtimestamp, nextval

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)
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

    # Add new request_event table
    try:
        RequestEvent_table.create()
    except Exception:
        log.exception("Creating request_event table failed.")
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

    if migrate_engine.name != 'sqlite':
        # Delete the state column
        try:
            Request_table = Table("request", metadata, autoload=True)
        except NoSuchTableError:
            Request_table = None
            log.debug("Failed loading table request")
        if Request_table is not None:
            try:
                Request_table.c.state.drop()
            except Exception:
                log.exception("Deleting column 'state' to request table failed.")


def downgrade(migrate_engine):
    pass
