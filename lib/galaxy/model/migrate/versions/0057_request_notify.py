"""
Migration script to modify the 'notify' field in the 'request' table from a boolean
to a JSONType
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from sqlalchemy.exc import *

from galaxy.model.custom_types import *
from galaxy.util.json import from_json_string, to_json_string

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )


def upgrade():
    print __doc__
    metadata.reflect()
    try:
        Request_table = Table( "request", metadata, autoload=True )
    except NoSuchTableError, e:
        Request_table = None
        log.debug( "Failed loading table 'request'" )
        

    if Request_table:
        # create the column again as JSONType
        try:
            col = Column( "notification", JSONType() )
            col.create( Request_table )
            assert col is Request_table.c.notification
        except Exception, e:
            log.debug( "Creating column 'notification' in the 'request' table failed: %s" % ( str( e ) ) )   

        cmd = "SELECT id, user_id, notify FROM request"
        result = db_session.execute( cmd )
        for r in result:
            id = int(r[0])
            notify_old = r[1]
            notify_new = dict(email=[], sample_states=[], body='', subject='')
            cmd = "update request set notification='%s' where id=%i" % (to_json_string(notify_new), id)
            db_session.execute( cmd )
        
        cmd = "SELECT id, notification FROM request"
        result = db_session.execute( cmd )
        for r in result:
            rr = from_json_string(str(r[1]))

        # remove the 'notify' column
        try:
            Request_table.c.notify.drop()
        except Exception, e:
            log.debug( "Deleting column 'notify' from the 'request' table failed: %s" % ( str( e ) ) )   
     
            

def downgrade():
    pass