"""
Migration script to create table for tracking history_dataset_association subsets.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

# Table to add.

HistoryDatasetAssociationSubset_table = Table( "history_dataset_association_subset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "history_dataset_association_subset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "location", Unicode(255), index=True)
)
    
def upgrade():
    print __doc__
    metadata.reflect()

    # Create history_dataset_association_subset.
    try:
        HistoryDatasetAssociationSubset_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating history_dataset_association_subset table failed: %s" % str( e ) )
                        
def downgrade():
    metadata.reflect()
    
    # Drop history_dataset_association_subset table.
    try:
        HistoryDatasetAssociationSubset_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping history_dataset_association_subset table failed: %s" % str( e ) )