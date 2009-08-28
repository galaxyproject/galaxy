"""
This migration script adds the tables necessary to support tagging of histories,
datasets, and history-dataset associations (user views of datasets).

If using mysql, this script will display the following error, which is corrected in the next
migration script:

history_dataset_association_tag_association table failed:  (OperationalError)
(1059, "Identifier name 'ix_history_dataset_association_tag_association_history_dataset_association_id'
is too long)
"""

from sqlalchemy import *
from migrate import *

import datetime
now = datetime.datetime.utcnow

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

def display_migration_details():
    print ""
    print "This migration script adds the tables necessary to support tagging of histories,"
    print "datasets, and history-dataset associations (user views of datasets)."
    print ""
    print "If using mysql, this script will display the following error, which is "
    print "corrected in the next migration script:"
    print "history_dataset_association_tag_association table failed:  "
    print "(OperationalError) (1059, 'Identifier name "
    print "'ix_history_dataset_association_tag_association_history_dataset_association_id'"
    print "is too long)"
    

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
    display_migration_details()
    metadata.reflect()
    try:
        Tag_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating tag table failed: %s" % str( e ) )
    try:
        HistoryTagAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating history_tag_association table failed: %s" % str( e ) )
    try:
        DatasetTagAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating dataset_tag_association table failed: %s" % str( e ) )
    try:
        HistoryDatasetAssociationTagAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating history_dataset_association_tag_association table failed: %s" % str( e ) )
    
def downgrade():
    metadata.reflect()
    try:
        Tag_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping tag table failed: %s" % str( e ) )
    try:
        HistoryTagAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping history_tag_association table failed: %s" % str( e ) )
    try:
        DatasetTagAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping dataset_tag_association table failed: %s" % str( e ) )
    try:
        HistoryDatasetAssociationTagAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping history_dataset_association_tag_association table failed: %s" % str( e ) )