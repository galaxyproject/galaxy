from sqlalchemy import *
from migrate import *

import datetime
now = datetime.datetime.utcnow

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

# New tables to support tagging of histories, datasets, and history-dataset associations.
Tag_table = Table( "tag", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "type", Integer ),
    Column( "parent_id", Integer, ForeignKey( "tag.id" ) ),
    Column( "name", TrimmedString(255) ), 
    UniqueConstraint( "name" ) )

HistoryTagAssociation_table = Table( "history_tag_association", metadata,
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )
    
DatasetTagAssociation_table = Table( "dataset_tag_association", metadata,
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

HistoryDatasetAssociationTagAssociation_table = Table( "history_dataset_association_tag_association", metadata,
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

def upgrade():
    metadata.reflect()
    Tag_table.create()
    HistoryTagAssociation_table.create()
    DatasetTagAssociation_table.create()
    HistoryDatasetAssociationTagAssociation_table.create()
    
def downgrade():
    metadata.reflect()
    Tag_table.drop()
    HistoryTagAssociation_table.drop()
    DatasetTagAssociation_table.drop()
    HistoryDatasetAssociationTagAssociation_table.drop()