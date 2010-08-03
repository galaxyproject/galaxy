"""
Migration script to create tables for rating histories, datasets, workflows, pages, and visualizations.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

# Rating tables.

HistoryRatingAssociation_table = Table( "history_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
HistoryDatasetAssociationRatingAssociation_table = Table( "history_dataset_association_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
StoredWorkflowRatingAssociation_table = Table( "stored_workflow_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
PageRatingAssociation_table = Table( "page_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
VisualizationRatingAssociation_table = Table( "visualization_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
def upgrade():
    print __doc__
    metadata.reflect()

    # Create history_rating_association table.
    try:
        HistoryRatingAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating history_rating_association table failed: %s" % str( e ) )
        
    # Create history_dataset_association_rating_association table.
    try:
        HistoryDatasetAssociationRatingAssociation_table.create()
    except Exception, e:
        # MySQL cannot handle long index names; when we see this error, create the index name manually.
        if migrate_engine.name == 'mysql' and \
            str(e).lower().find("identifier name 'ix_history_dataset_association_rating_association_history_dataset_association_id' is too long"):
            i = Index( "ix_hda_rating_association_hda_id", HistoryDatasetAssociationRatingAssociation_table.c.history_dataset_association_id )
            try:
                i.create()
            except Exception, e:
                print str(e)
                log.debug( "Adding index 'ix_hda_rating_association_hda_id' to table 'history_dataset_association_rating_association' table failed: %s" % str( e ) )
        else:
            print str(e)
            log.debug( "Creating history_dataset_association_rating_association table failed: %s" % str( e ) )    
        
    # Create stored_workflow_rating_association table.
    try:
        StoredWorkflowRatingAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating stored_workflow_rating_association table failed: %s" % str( e ) )
        
    # Create page_rating_association table.
    try:
        PageRatingAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating page_rating_association table failed: %s" % str( e ) )
        
    # Create visualization_rating_association table.
    try:
        VisualizationRatingAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating visualization_rating_association table failed: %s" % str( e ) )
                
def downgrade():
    metadata.reflect()
        
    # Drop history_rating_association table.
    try:
       HistoryRatingAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping history_rating_association table failed: %s" % str( e ) )

    # Drop history_dataset_association_rating_association table.
    try:
       HistoryDatasetAssociationRatingAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping history_dataset_association_rating_association table failed: %s" % str( e ) )    

    # Drop stored_workflow_rating_association table.
    try:
       StoredWorkflowRatingAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping stored_workflow_rating_association table failed: %s" % str( e ) )

    # Drop page_rating_association table.
    try:
       PageRatingAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping page_rating_association table failed: %s" % str( e ) )    
   
    # Drop visualization_rating_association table.
    try:
       VisualizationRatingAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping visualization_rating_association table failed: %s" % str( e ) )