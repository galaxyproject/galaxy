"""
Migration script to modify the 'notify' field in the 'request' table from a boolean
to a JSONType
"""
from __future__ import print_function

import logging
from json import dumps

from sqlalchemy import (
    Boolean,
    Column,
    MetaData,
    Table
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column,
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    Request_table = Table("request", metadata, autoload=True)

    # create the column again as JSONType
    col = Column("notification", JSONType())
    add_column(col, Request_table)

    cmd = "SELECT id, user_id, notify FROM request"
    result = migrate_engine.execute(cmd)
    for r in result:
        id = int(r[0])
        notify_new = dict(email=[], sample_states=[], body='', subject='')
        cmd = "UPDATE request SET notification='%s' WHERE id=%i" % (dumps(notify_new), id)
        migrate_engine.execute(cmd)

    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        drop_column('notify', Request_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    Request_table = Table("request", metadata, autoload=True)
    if migrate_engine.name != 'sqlite':
        c = Column("notify", Boolean, default=False)
        add_column(c, Request_table)

    drop_column('notification', Request_table)
