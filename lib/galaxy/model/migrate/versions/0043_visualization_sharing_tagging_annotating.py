"""
Migration script to create tables and columns for sharing visualizations.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

# Sharing visualizations.

VisualizationUserShareAssociation_table = Table( "visualization_user_share_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )
    
# Tagging visualizations.

VisualizationTagAssociation_table = Table( "visualization_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True) )

# Annotating visualizations.

VisualizationAnnotationAssociation_table = Table( "visualization_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=False ) )
    
Visualiation_table = Table( "visualization", metadata, autoload=True )
    
def upgrade():
    print __doc__
    metadata.reflect()

    # Create visualization_user_share_association table.
    try:
        VisualizationUserShareAssociation_table.create()
    except Exception, e:
        print "Creating visualization_user_share_association table failed: %s" % str( e )
        log.debug( "Creating visualization_user_share_association table failed: %s" % str( e ) )
        
    # Get default boolean value 'false' so that columns can be initialized.
    if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
        default_false = "0"
    elif migrate_engine.name == 'postgres':
        default_false = "false"
        
    # Add columns & create indices for supporting sharing to visualization table.
    deleted_column = Column( "deleted", Boolean, default=False, index=True )
    importable_column = Column( "importable", Boolean, default=False, index=True )
    slug_column = Column( "slug", TEXT, index=True )
    published_column = Column( "published", Boolean, index=True )
    
    try:
        # Add column.
        deleted_column.create( Visualiation_table )
        assert deleted_column is Visualiation_table.c.deleted
	    
        # Fill column with default value.
        cmd = "UPDATE visualization SET deleted = %s" % default_false
        db_session.execute( cmd )
    except Exception, e:
        print "Adding deleted column to visualization table failed: %s" % str( e )
        log.debug( "Adding deleted column to visualization table failed: %s" % str( e ) )
        
    try:
        i = Index( "ix_visualization_deleted", Visualiation_table.c.deleted )
        i.create()
    except Exception, e:
        print "Adding index 'ix_visualization_deleted' failed: %s" % str( e )
        log.debug( "Adding index 'ix_visualization_deleted' failed: %s" % str( e ) )
	    
    try:
        # Add column.
        importable_column.create( Visualiation_table )
        assert importable_column is Visualiation_table.c.importable

        # Fill column with default value.
        cmd = "UPDATE visualization SET importable = %s" % default_false
        db_session.execute( cmd )
    except Exception, e:
        print "Adding importable column to visualization table failed: %s" % str( e )
        log.debug( "Adding importable column to visualization table failed: %s" % str( e ) )
        
    i = Index( "ix_visualization_importable", Visualiation_table.c.importable )
    try:
        i.create()
    except Exception, e:
        print "Adding index 'ix_visualization_importable' failed: %s" % str( e )
        log.debug( "Adding index 'ix_visualization_importable' failed: %s" % str( e ) )
	    
    try:
	    slug_column.create( Visualiation_table )
	    assert slug_column is Visualiation_table.c.slug
    except Exception, e:
        print "Adding slug column to visualization table failed: %s" % str( e )
        log.debug( "Adding slug column to visualization table failed: %s" % str( e ) )
                
    try:
        if migrate_engine.name == 'mysql':
            # Have to create index manually.
            cmd = "CREATE INDEX ix_visualization_slug ON visualization ( slug ( 100 ) )"
            db_session.execute( cmd )
        else:
            i = Index( "ix_visualization_slug", Visualiation_table.c.slug )
            i.create()
    except Exception, e:
        print "Adding index 'ix_visualization_slug' failed: %s" % str( e )
        log.debug( "Adding index 'ix_visualization_slug' failed: %s" % str( e ) )
	    
    try:
        # Add column.
        published_column.create( Visualiation_table )
        assert published_column is Visualiation_table.c.published

        # Fill column with default value.
        cmd = "UPDATE visualization SET published = %s" % default_false
        db_session.execute( cmd )
    except Exception, e:
        print "Adding published column to visualization table failed: %s" % str( e )
        log.debug( "Adding published column to visualization table failed: %s" % str( e ) )
        
    i = Index( "ix_visualization_published", Visualiation_table.c.published )
    try:
        i.create()
    except Exception, e:
        print "Adding index 'ix_visualization_published' failed: %s" % str( e )
        log.debug( "Adding index 'ix_visualization_published' failed: %s" % str( e ) )
        
    # Create visualization_tag_association table.
    try:
        VisualizationTagAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating visualization_tag_association table failed: %s" % str( e ) )
        
    # Create visualization_annotation_association table.
    try:
        VisualizationAnnotationAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating visualization_annotation_association table failed: %s" % str( e ) )

    # Need to create index for visualization annotation manually to deal with errors.
    try:
       if migrate_engine.name == 'mysql':
           # Have to create index manually.
           cmd = "CREATE INDEX ix_visualization_annotation_association_annotation ON visualization_annotation_association ( annotation ( 100 ) )"
           db_session.execute( cmd )
       else:
           i = Index( "ix_visualization_annotation_association_annotation", VisualizationAnnotationAssociation_table.c.annotation )
           i.create()
    except Exception, e:
       print "Adding index 'ix_visualization_annotation_association_annotation' failed: %s" % str( e )
       log.debug( "Adding index 'ix_visualization_annotation_association_annotation' failed: %s" % str( e ) )
                       
def downgrade():
    metadata.reflect()
        
    # Drop visualization_user_share_association table.
    try:
        VisualizationUserShareAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping visualization_user_share_association table failed: %s" % str( e ) )

    # Drop columns for supporting sharing from visualization table.
    try:
	    Visualiation_table.c.deleted.drop()
    except Exception, e:
        print "Dropping deleted column from visualization table failed: %s" % str( e )
        log.debug( "Dropping deleted column from visualization table failed: %s" % str( e ) )

    try:
	    Visualiation_table.c.importable.drop()
    except Exception, e:
        print "Dropping importable column from visualization table failed: %s" % str( e )
        log.debug( "Dropping importable column from visualization table failed: %s" % str( e ) )

    try:
	    Visualiation_table.c.slug.drop()
    except Exception, e:
        print "Dropping slug column from visualization table failed: %s" % str( e )
        log.debug( "Dropping slug column from visualization table failed: %s" % str( e ) )

    try:
	    Visualiation_table.c.published.drop()
    except Exception, e:
        print "Dropping published column from visualization table failed: %s" % str( e )
        log.debug( "Dropping published column from visualization table failed: %s" % str( e ) )
        
    # Drop visualization_tag_association table.
    try:
        VisualizationTagAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping visualization_tag_association table failed: %s" % str( e ) )

    # Drop visualization_annotation_association table.
    try:
        VisualizationAnnotationAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping visualization_annotation_association table failed: %s" % str( e ) )