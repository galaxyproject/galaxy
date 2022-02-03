"""
Migration script to add the api_keys table.
"""

import datetime
import logging
import sys

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
)

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)

now = datetime.datetime.utcnow

metadata = MetaData()

APIKeys_table = Table(
    "api_keys",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("key", TrimmedString(32), index=True, unique=True),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        APIKeys_table.create()
    except Exception:
        log.exception("Creating api_keys table failed.")


def downgrade(migrate_engine):
    # Load existing tables
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        APIKeys_table.drop()
    except Exception:
        log.exception("Dropping api_keys table failed.")
