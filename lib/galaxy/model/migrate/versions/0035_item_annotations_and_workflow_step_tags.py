"""
Migration script to (a) create tables for annotating objects and (b) create tags for workflow steps.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

# Annotation tables.

HistoryAnnotationAssociation_table = Table( "history_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT ) )

HistoryDatasetAssociationAnnotationAssociation_table = Table( "history_dataset_association_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT ) )

StoredWorkflowAnnotationAssociation_table = Table( "stored_workflow_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT ) )

WorkflowStepAnnotationAssociation_table = Table( "workflow_step_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT ) )

# Tagging tables.

WorkflowStepTagAssociation_table = Table( "workflow_step_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    # Create history_annotation_association table.
    try:
        HistoryAnnotationAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating history_annotation_association table failed: %s" % str( e ) )

    # Create history_dataset_association_annotation_association table.
    try:
        HistoryDatasetAssociationAnnotationAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating history_dataset_association_annotation_association table failed: %s" % str( e ) )

    # Create stored_workflow_annotation_association table.
    try:
        StoredWorkflowAnnotationAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating stored_workflow_annotation_association table failed: %s" % str( e ) )

    # Create workflow_step_annotation_association table.
    try:
        WorkflowStepAnnotationAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating workflow_step_annotation_association table failed: %s" % str( e ) )

    # Create workflow_step_tag_association table.
    try:
        WorkflowStepTagAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating workflow_step_tag_association table failed: %s" % str( e ) )

    haaa = Index( "ix_history_anno_assoc_annotation", HistoryAnnotationAssociation_table.c.annotation, mysql_length = 200)
    hdaaa = Index( "ix_history_dataset_anno_assoc_annotation", HistoryDatasetAssociationAnnotationAssociation_table.c.annotation, mysql_length = 200)
    swaaa = Index( "ix_stored_workflow_ann_assoc_annotation", StoredWorkflowAnnotationAssociation_table.c.annotation, mysql_length = 200)
    wsaaa = Index( "ix_workflow_step_ann_assoc_annotation", WorkflowStepAnnotationAssociation_table.c.annotation, mysql_length = 200)

    try:
        haaa.create()
        hdaaa.create()
        swaaa.create()
        wsaaa.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating annotation indices failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop history_annotation_association table.
    try:
       HistoryAnnotationAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping history_annotation_association table failed: %s" % str( e ) )

    # Drop history_dataset_association_annotation_association table.
    try:
       HistoryDatasetAssociationAnnotationAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping history_dataset_association_annotation_association table failed: %s" % str( e ) )

    # Drop stored_workflow_annotation_association table.
    try:
       StoredWorkflowAnnotationAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping stored_workflow_annotation_association table failed: %s" % str( e ) )

    # Drop workflow_step_annotation_association table.
    try:
       WorkflowStepAnnotationAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping workflow_step_annotation_association table failed: %s" % str( e ) )

    # Drop workflow_step_tag_association table.
    try:
       WorkflowStepTagAssociation_table.drop()
    except Exception, e:
       print str(e)
       log.debug( "Dropping workflow_step_tag_association table failed: %s" % str( e ) )

