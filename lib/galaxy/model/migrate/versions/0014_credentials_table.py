from sqlalchemy import *
from migrate import *

import datetime
now = datetime.datetime.utcnow

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

Credentials_table = Table( "stored_user_credentials", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "name", TEXT),
    Column( "access_key", TEXT),
    Column( "secret_key", TEXT) )

def upgrade():
    metadata.reflect()
    Credentials_table.create()

def downgrade():
    metadata.reflect()
    Credentials_table.drop()
