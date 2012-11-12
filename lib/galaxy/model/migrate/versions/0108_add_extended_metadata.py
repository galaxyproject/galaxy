"""
Add the ExtendedMetadata and ExtendedMetadataIndex tables 
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import JSONType

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
#db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )


ExtendedMetadata_table = Table("extended_metadata", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "data", JSONType ) )

ExtendedMetadataIndex_table = Table("extended_metadata_index", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "extended_metadata_id", Integer, ForeignKey("extended_metadata.id",
                                                        onupdate="CASCADE",
                                                        ondelete="CASCADE" ),
                                             index=True ),
    Column( "path", String( 255 )),
    Column( "value", TEXT))

extended_metadata_ldda_col = Column( "extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), nullable=True )


def display_migration_details():
    print ""
    print "This migration script adds a 'handler' column to the Job table."

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        ExtendedMetadata_table.create()
    except:
        log.debug("Could not create ExtendedMetadata Table.")
    try:
        ExtendedMetadataIndex_table.create()
    except:
        log.debug("Could not create ExtendedMetadataIndex Table.")

    
    # Add the extended_metadata_id to the ldda table
    try:
        ldda_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
        extended_metadata_ldda_col.create( ldda_table )
        assert extended_metadata_ldda_col is ldda_table.c.extended_metadata_id
    except Exception, e:
        print str(e)
        log.error( "Adding column 'extended_metadata_id' to library_dataset_dataset_association table failed: %s" % str( e ) )
        return 


def downgrade():
    metadata.reflect()
    ExtendedMetadata_table.drop()
    ExtendedMetadataIndex_table.drop()
    
    # Drop the Job table's exit_code column. 
    try:
        job_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
        extended_metadata_id = job_table.c.extended_metadata_id
        extended_metadata_id.drop()
    except Exception, e:
        log.debug( "Dropping 'extended_metadata_id' column from library_dataset_dataset_association table failed: %s" % ( str( e ) ) )


