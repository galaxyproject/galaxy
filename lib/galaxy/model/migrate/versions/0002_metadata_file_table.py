from sqlalchemy import *
from migrate import *

import datetime
now = datetime.datetime.utcnow

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

# New table in changeset 1568:0b022adfdc34
MetadataFile_table = Table( "metadata_file", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "name", TEXT ),
    Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    MetadataFile_table.create()

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    MetadataFile_table.drop()
