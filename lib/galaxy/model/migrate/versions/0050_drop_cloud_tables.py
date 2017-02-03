from __future__ import print_function

import datetime
import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()


def display_migration_details():
    print
    print("========================================")
    print("This script drops tables that were associated with the old Galaxy Cloud functionality.")
    print("========================================")


CloudImage_table = Table( "cloud_image", metadata,
                          Column( "id", Integer, primary_key=True ),
                          Column( "create_time", DateTime, default=now ),
                          Column( "update_time", DateTime, default=now, onupdate=now ),
                          Column( "provider_type", TEXT ),
                          Column( "image_id", TEXT, nullable=False ),
                          Column( "manifest", TEXT ),
                          Column( "state", TEXT ),
                          Column( "architecture", TEXT ),
                          Column( "deleted", Boolean, default=False ) )

""" UserConfiguredInstance (UCI) table """
UCI_table = Table( "cloud_uci", metadata,
                   Column( "id", Integer, primary_key=True ),
                   Column( "create_time", DateTime, default=now ),
                   Column( "update_time", DateTime, default=now, onupdate=now ),
                   Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
                   Column( "credentials_id", Integer, ForeignKey( "cloud_user_credentials.id" ), index=True ),
                   Column( "key_pair_name", TEXT ),
                   Column( "key_pair_material", TEXT ),
                   Column( "name", TEXT ),
                   Column( "state", TEXT ),
                   Column( "error", TEXT ),
                   Column( "total_size", Integer ),
                   Column( "launch_time", DateTime ),
                   Column( "deleted", Boolean, default=False ) )

CloudInstance_table = Table( "cloud_instance", metadata,
                             Column( "id", Integer, primary_key=True ),
                             Column( "create_time", DateTime, default=now ),
                             Column( "update_time", DateTime, default=now, onupdate=now ),
                             Column( "launch_time", DateTime ),
                             Column( "stop_time", DateTime ),
                             Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
                             Column( "uci_id", Integer, ForeignKey( "cloud_uci.id" ), index=True ),
                             Column( "type", TEXT ),
                             Column( "reservation_id", TEXT ),
                             Column( "instance_id", TEXT ),
                             Column( "mi_id", Integer, ForeignKey( "cloud_image.id" ), index=True ),
                             Column( "state", TEXT ),
                             Column( "error", TEXT ),
                             Column( "public_dns", TEXT ),
                             Column( "private_dns", TEXT ),
                             Column( "security_group", TEXT ),
                             Column( "availability_zone", TEXT ) )

CloudStore_table = Table( "cloud_store", metadata,
                          Column( "id", Integer, primary_key=True ),
                          Column( "create_time", DateTime, default=now ),
                          Column( "update_time", DateTime, default=now, onupdate=now ),
                          Column( "attach_time", DateTime ),
                          Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
                          Column( "uci_id", Integer, ForeignKey( "cloud_uci.id" ), index=True, nullable=False ),
                          Column( "volume_id", TEXT ),
                          Column( "size", Integer, nullable=False ),
                          Column( "availability_zone", TEXT ),
                          Column( "inst_id", Integer, ForeignKey( "cloud_instance.id" ) ),
                          Column( "status", TEXT ),
                          Column( "device", TEXT ),
                          Column( "space_consumed", Integer ),
                          Column( "error", TEXT ),
                          Column( "deleted", Boolean, default=False ) )

CloudSnapshot_table = Table( "cloud_snapshot", metadata,
                             Column( "id", Integer, primary_key=True ),
                             Column( "create_time", DateTime, default=now ),
                             Column( "update_time", DateTime, default=now, onupdate=now ),
                             Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
                             Column( "uci_id", Integer, ForeignKey( "cloud_uci.id" ), index=True ),
                             Column( "store_id", Integer, ForeignKey( "cloud_store.id" ), index=True, nullable=False ),
                             Column( "snapshot_id", TEXT ),
                             Column( "status", TEXT ),
                             Column( "description", TEXT ),
                             Column( "error", TEXT ),
                             Column( "deleted", Boolean, default=False ) )

CloudUserCredentials_table = Table( "cloud_user_credentials", metadata,
                                    Column( "id", Integer, primary_key=True ),
                                    Column( "create_time", DateTime, default=now ),
                                    Column( "update_time", DateTime, default=now, onupdate=now ),
                                    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
                                    Column( "provider_id", Integer, ForeignKey( "cloud_provider.id" ), index=True, nullable=False ),
                                    Column( "name", TEXT ),
                                    Column( "access_key", TEXT ),
                                    Column( "secret_key", TEXT ),
                                    Column( "deleted", Boolean, default=False ) )

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
                             Column( "path", TEXT ),
                             Column( "deleted", Boolean, default=False ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    try:
        CloudSnapshot_table.drop()
        CloudStore_table.drop()
        CloudInstance_table.drop()
        CloudImage_table.drop()
        UCI_table.drop()
        CloudUserCredentials_table.drop()
        CloudProvider_table.drop()
    except Exception as e:
        log.debug( "Dropping cloud tables failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
