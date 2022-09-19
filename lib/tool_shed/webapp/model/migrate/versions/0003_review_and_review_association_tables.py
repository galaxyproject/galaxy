"""
Adds the tool_rating_association table, enabling tools to be rated along with review comments.
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
    TEXT,
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

ToolRatingAssociation_table = Table(
    "tool_rating_association",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("tool_id", Integer, ForeignKey("tool.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("rating", Integer, index=True),
    Column("comment", TEXT),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    # Load existing tables
    metadata.reflect()
    try:
        ToolRatingAssociation_table.create()
    except Exception:
        log.exception("Creating tool_rating_association table failed.")


def downgrade(migrate_engine):
    # Load existing tables
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        ToolRatingAssociation_table.drop()
    except Exception:
        log.exception("Dropping tool_rating_association table failed.")
