"""
This script fixes a problem introduced in 0015_tagging.py. MySQL has a name length
limit and thus the index "ix_hda_ta_history_dataset_association_id" has to be
manually created.
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
    print "This script fixes a problem introduced in 0015_tagging.py.  MySQL has a"
    print "name length limit and thus the index 'ix_hda_ta_history_dataset_association_id'"
    print "has to be manually created."
    
HistoryDatasetAssociationTagAssociation_table = Table( "history_dataset_association_tag_association", metadata,
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

def upgrade():
    display_migration_details()
    metadata.reflect()
    i = Index( "ix_hda_ta_history_dataset_association_id", HistoryDatasetAssociationTagAssociation_table.c.history_dataset_association_id )
    try:
        i.create()
    except Exception, e:
        print str(e)
        log.debug( "Adding index 'ix_hdata_history_dataset_association_id' to table 'history_dataset_association_tag_association' table failed: %s" % str( e ) )
    
def downgrade():
    metadata.reflect()
    i = Index( "ix_hda_ta_history_dataset_association_id", HistoryDatasetAssociationTagAssociation_table.c.history_dataset_association_id )
    try:
        i.drop()
    except Exception, e:
        print str(e)
        log.debug( "Removing index 'ix_hdata_history_dataset_association_id' to table 'history_dataset_association_tag_association' table failed: %s" % str( e ) )