from sqlalchemy import *
from migrate import *

import datetime
now = datetime.datetime.utcnow

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

CloudImage_table = Table( "cloud_image", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "image_id", TEXT, nullable=False ),
    Column( "manifest", TEXT ),
    Column( "state", TEXT ) )

CloudInstance_table = Table( "cloud_instance", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "launch_time", DateTime ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "name", TEXT ),
    Column( "type", TEXT ),
    Column( "reservation_id", TEXT ),
    Column( "instance_id", TEXT ),
    Column( "mi", TEXT, ForeignKey( "cloud_image.image_id" ), index=True, nullable=False ),
    Column( "state", TEXT ),
    Column( "public_dns", TEXT ),
    Column( "private_dns", TEXT ),
    Column( "keypair_name", TEXT ),
    Column( "availability_zone", TEXT ) )

CloudStorage_table = Table( "cloud_storage", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "attach_time", DateTime ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "volume_id", TEXT, nullable=False ),
    Column( "size", Integer, nullable=False ),
    Column( "availability_zone", TEXT, nullable=False ),
    Column( "i_id", TEXT, ForeignKey( "cloud_instance.instance_id" ), index=True ),
    Column( "status", TEXT ),
    Column( "device", TEXT ),
    Column( "space_consumed", Integer )
    )

CloudUserCredentials_table = Table( "cloud_user_credentials", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "name", TEXT),
    Column( "access_key", TEXT),
    Column( "secret_key", TEXT),
    Column( "defaultCred", Boolean, default=False)
    )
def upgrade():
    metadata.reflect()
    CloudUserCredentials_table.create()
    CloudInstance_table.create()
    CloudStorage_table.create()
    try:
        CloudImage_table.create()
    except Exception, e:
        log.debug( "Creating cloud_image table failed. Table probably exists already." )

def downgrade():
    metadata.reflect()
    try:
        CloudImage_table.drop()
    except Exception, e:
        log.debug( "Dropping cloud_image table failed: %s" % str( e ) ) 
    
    try:
        CloudInstance_table.drop()
    except Exception, e:
        log.debug( "Dropping cloud_instance table failed: %s" % str( e ) )  
        
    try:
        CloudStorage_table.drop()
    except Exception, e:
        log.debug( "Dropping cloud_user_credentials table failed: %s" % str( e ) )  
        
    try:
        log.deboug( "Would drop cloud user credentials table." )
        #CloudUserCredentials_table.drop()
    except Exception, e:
        log.debug( "Dropping cloud_user_credentials table failed: %s" % str( e ) )  
        
    
        
    
