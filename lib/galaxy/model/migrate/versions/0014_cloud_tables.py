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

UCI_table = Table( "cloud_uci", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "credentials_id", Integer, ForeignKey( "cloud_user_credentials.id" ), index=True ),
    Column( "name", TEXT ),
    Column( "state", TEXT ),
    Column( "error", TEXT ),
    Column( "total_size", Integer ),
    Column( "launch_time", DateTime ) )

CloudInstance_table = Table( "cloud_instance", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "launch_time", DateTime ),
    Column( "stop_time", DateTime ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "uci_id", Integer, ForeignKey( "uci.id" ), index=True ),
    Column( "type", TEXT ),
    Column( "reservation_id", TEXT ),
    Column( "instance_id", TEXT ),
    Column( "mi_id", TEXT, ForeignKey( "cloud_image.image_id" ), index=True, nullable=False ),
    Column( "state", TEXT ),
    Column( "error", TEXT ),
    Column( "public_dns", TEXT ),
    Column( "private_dns", TEXT ),
    Column( "keypair_name", TEXT ),
    Column( "keypair_material", TEXT ),
    Column( "availability_zone", TEXT ) )

CloudStore_table = Table( "cloud_store", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "attach_time", DateTime ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "uci_id", Integer, ForeignKey( "uci.id" ), index=True, nullable=False ),
    Column( "volume_id", TEXT ),
    Column( "size", Integer, nullable=False ),
    Column( "availability_zone", TEXT ),
    Column( "i_id", TEXT, ForeignKey( "cloud_instance.instance_id" ), index=True ),
    Column( "status", TEXT ),
    Column( "device", TEXT ),
    Column( "space_consumed", Integer ) )

CloudUserCredentials_table = Table( "cloud_user_credentials", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "name", TEXT ),
    Column( "access_key", TEXT ),
    Column( "secret_key", TEXT ),
    Column( "defaultCred", Boolean, default=False ),
    Column( "provider_id", Integer, ForeignKey( "cloud_provider.id" ), index=True, nullable=False ) )

CloudProvider_table = Table( "cloud_provider", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "type", TEXT, nullable=False ),
    Column( "name", TEXT ),
    Column( "region_connection", TEXT ),
    Column( "region_name", TEXT ),
    Column( "region_endpoint", TEXT ),
    Column( "is_secure", Boolean ),
    Column( "host", TEXT ),
    Column( "port", Integer ),
    Column( "proxy", TEXT ),
    Column( "proxy_port", TEXT ),
    Column( "proxy_user", TEXT ),
    Column( "proxy_pass", TEXT ),
    Column( "debug", Integer ),
    Column( "https_connection_factory", TEXT ),
    Column( "path", TEXT ) )

def upgrade():
    metadata.reflect()
    
    CloudImage_table.create()
    UCI_table.create()
    CloudUserCredentials_table.create()
    CloudProvider_table.create()
    CloudInstance_table.create()
    CloudStore_table.create()
    
def downgrade():
    metadata.reflect()
    
    CloudImage_table.drop() 
    CloudInstance_table.drop()
    CloudStore_table.drop()
    CloudUserCredentials_table.drop() 
    UCI_table.drop()
    CloudProvider_table.drop()