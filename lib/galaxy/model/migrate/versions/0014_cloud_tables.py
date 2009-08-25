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
    Column( "secret_key", TEXT),
    Column( "defaultCred", Boolean, default=False ) )

UserInstances_table = Table ( "user_instances", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "launch_time", DateTime, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "name", TEXT ),
    Column( "reservation_id", TEXT ),
    Column( "instance_id", TEXT ),
    Column( "ami", TEXT, ForeignKey( "cloud_images.image_id" ), nullable=False ),
    Column( "state", TEXT ),
    Column( "public_dns", TEXT ),
    Column( "private_dns", TEXT ),
    Column( "keypair_fingerprint", TEXT ),
    Column( "keypair_material", TEXT ),
    Column( "availability_zone", TEXT ) )

CloudImages_table = Table( "cloud_images", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "upadte_time", DateTime, default=now, onupdate=now ),
    Column( "image_id", TEXT, nullable=False ),
    Column( "manifest", TEXT ),
    Column( "state", TEXT ) )
    
def upgrade():
    metadata.reflect()
    Credentials_table.create()
    UserInstances_table.create()
    try:
        CloudImages_table.create()
    except Exception, e:
        log.debug( "Creating CloudImages table failed. Table probably exists already." )

def downgrade():
    metadata.reflect()
    try:
        Credentials_table.drop()
    except Exception, e:
        log.debug( "Dropping stored_user_credentials table failed: %s" % str( e ) )  
        
    try:
        UserInstances_table.drop()
    except Exception, e:
        log.debug( "Dropping user_instances table failed: %s" % str( e ) )  
