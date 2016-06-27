"""
Migration script to add the job_to_input_library_dataset table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table

log = logging.getLogger( __name__ )

metadata = MetaData()

JobToInputLibraryDatasetAssociation_table = Table( "job_to_input_library_dataset", metadata,
                                                   Column( "id", Integer, primary_key=True ),
                                                   Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
                                                   Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True ),
                                                   Column( "name", String(255) ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create the job_to_input_library_dataset table
    try:
        JobToInputLibraryDatasetAssociation_table.create()
    except Exception as e:
        print("Creating job_to_input_library_dataset table failed: %s" % str( e ))
        log.debug( "Creating job_to_input_library_dataset table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the job_to_input_library_dataset table
    try:
        JobToInputLibraryDatasetAssociation_table.drop()
    except Exception as e:
        print(str(e))
        log.debug( "Dropping job_to_input_library_dataset table failed: %s" % str( e ) )
