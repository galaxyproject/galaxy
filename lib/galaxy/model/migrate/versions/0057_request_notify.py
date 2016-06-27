"""
Migration script to modify the 'notify' field in the 'request' table from a boolean
to a JSONType
"""
from __future__ import print_function

import datetime
import logging
from json import dumps

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.custom_types import JSONType

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        Request_table = Table( "request", metadata, autoload=True )
    except NoSuchTableError:
        Request_table = None
        log.debug( "Failed loading table 'request'" )

    if Request_table is not None:
        # create the column again as JSONType
        try:
            col = Column( "notification", JSONType() )
            col.create( Request_table )
            assert col is Request_table.c.notification
        except Exception as e:
            log.debug( "Creating column 'notification' in the 'request' table failed: %s" % ( str( e ) ) )

        cmd = "SELECT id, user_id, notify FROM request"
        result = migrate_engine.execute( cmd )
        for r in result:
            id = int(r[0])
            notify_new = dict(email=[], sample_states=[], body='', subject='')
            cmd = "UPDATE request SET notification='%s' WHERE id=%i" % (dumps(notify_new), id)
            migrate_engine.execute( cmd )

        # remove the 'notify' column for non-sqlite databases.
        if migrate_engine.name != 'sqlite':
            try:
                Request_table.c.notify.drop()
            except Exception as e:
                log.debug( "Deleting column 'notify' from the 'request' table failed: %s" % ( str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
