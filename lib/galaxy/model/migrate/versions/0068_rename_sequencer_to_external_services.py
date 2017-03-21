"""
This migration script renames the sequencer table to 'external_service' table and
creates a association table, 'request_type_external_service_association' and
populates it. The 'sequencer_id' foreign_key from the 'request_type' table is removed.
The 'sequencer_type_id' column is renamed to 'external_service_type_id' in the renamed
table 'external_service'. Finally, adds a foreign key to the external_service table in the
sample_dataset table and populates it.
"""
from __future__ import print_function

import datetime
import logging

from migrate import ForeignKeyConstraint
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table
from sqlalchemy.exc import NoSuchTableError

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()


def nextval( migrate_engine, table, col='id' ):
    if migrate_engine.name in ['postgres', 'postgresql']:
        return "nextval('%s_%s_seq')" % ( table, col )
    elif migrate_engine.name in ['mysql', 'sqlite']:
        return "null"
    else:
        raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    # Load existing tables
    metadata.reflect()
    # create the column. Call it external_services_id as the table 'sequencer' is
    # going to be renamed to 'external_service'
    try:
        SampleDataset_table = Table( "sample_dataset", metadata, autoload=True )
        col = Column( "external_service_id", Integer, index=True )
        col.create( SampleDataset_table, index_name="ix_sample_dataset_external_service_id" )
        assert col is SampleDataset_table.c.external_service_id
    except Exception:
        log.exception("Creating column 'external_service_id' in the 'sample_dataset' table failed.")
    if migrate_engine.name != 'sqlite':
        # Add a foreign key to the external_service table in the sample_dataset table
        try:
            Sequencer_table = Table( "sequencer", metadata, autoload=True )
            cons = ForeignKeyConstraint( [SampleDataset_table.c.external_service_id],
                                         [Sequencer_table.c.id],
                                         name='sample_dataset_external_services_id_fk' )
            # Create the constraint
            cons.create()
        except Exception:
            log.exception("Adding foreign key constraint 'sample_dataset_external_services_id_fk' to table 'sample_dataset' failed.")
    # populate the column
    cmd = "SELECT sample_dataset.id, request_type.sequencer_id " \
          + " FROM sample_dataset, sample, request, request_type " \
          + " WHERE sample.id=sample_dataset.sample_id and request.id=sample.request_id and request.request_type_id=request_type.id " \
          + " ORDER BY sample_dataset.id"
    try:
        result = migrate_engine.execute( cmd )
        for r in result:
            sample_dataset_id = int(r[0])
            sequencer_id = int(r[1])
            cmd = "UPDATE sample_dataset SET external_service_id='%i' where id=%i" % ( sequencer_id, sample_dataset_id )
            migrate_engine.execute( cmd )
        # rename 'sequencer' table to 'external_service'
        cmd = "ALTER TABLE sequencer RENAME TO external_service"
        migrate_engine.execute( cmd )
    except Exception:
        log.exception("Exception executing SQL command: %s" % cmd)
    # if running postgres then rename the primary key sequence too
    if migrate_engine.name in ['postgres', 'postgresql']:
        cmd = "ALTER TABLE sequencer_id_seq RENAME TO external_service_id_seq"
        migrate_engine.execute( cmd )
    # rename 'sequencer_type_id' column to 'external_service_type_id' in the table 'external_service'
    # create the column as 'external_service_type_id'
    try:
        ExternalServices_table = Table( "external_service", metadata, autoload=True )
        col = Column( "external_service_type_id", TrimmedString( 255 ) )
        col.create( ExternalServices_table )
        assert col is ExternalServices_table.c.external_service_type_id
    except Exception:
        log.exception("Creating column 'external_service_type_id' in the 'external_service' table failed.")
    # populate this new column
    cmd = "UPDATE external_service SET external_service_type_id=sequencer_type_id"
    migrate_engine.execute( cmd )
    # remove the 'sequencer_type_id' column
    try:
        ExternalServices_table.c.sequencer_type_id.drop()
    except Exception:
        log.exception("Deleting column 'sequencer_type_id' from the 'external_service' table failed.")
    # create 'request_type_external_service_association' table
    RequestTypeExternalServiceAssociation_table = Table( "request_type_external_service_association", metadata,
                                                         Column( "id", Integer, primary_key=True ),
                                                         Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ),
                                                         Column( "external_service_id", Integer, ForeignKey( "external_service.id" ), index=True ) )
    try:
        RequestTypeExternalServiceAssociation_table.create()
    except Exception:
        log.exception("Creating request_type_external_service_association table failed.")
    try:
        RequestTypeExternalServiceAssociation_table = Table( "request_type_external_service_association", metadata, autoload=True )
    except NoSuchTableError:
        RequestTypeExternalServiceAssociation_table = None
        log.debug( "Failed loading table request_type_external_service_association" )
    if RequestTypeExternalServiceAssociation_table is None:
        return
    # populate 'request_type_external_service_association' table
    cmd = "SELECT id, sequencer_id FROM request_type ORDER BY id ASC"
    result = migrate_engine.execute( cmd )
    results_list = result.fetchall()
    # Proceed only if request_types exists
    if len( results_list ):
        for row in results_list:
            request_type_id = row[0]
            sequencer_id = row[1]
            if not sequencer_id:
                sequencer_id = 'null'
            cmd = "INSERT INTO request_type_external_service_association VALUES ( %s, %s, %s )"
            cmd = cmd % ( nextval( migrate_engine, 'request_type_external_service_association' ),
                          request_type_id,
                          sequencer_id )
            migrate_engine.execute( cmd )
    # drop the 'sequencer_id' column in the 'request_type' table
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
        RequestType_table.c.sequencer_id.drop()
    except Exception:
        log.exception("Deleting column 'sequencer_id' from the 'request_type' table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    # Load existing tables
    metadata.reflect()
    # load sequencer & request_type table
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
    except NoSuchTableError:
        RequestType_table = None
        log.debug( "Failed loading table request_type" )
    if RequestType_table is None:
        return
    try:
        ExternalServices_table = Table( "external_service", metadata, autoload=True )
    except NoSuchTableError:
        ExternalServices_table = None
        log.debug( "Failed loading table 'external_service'" )
    if ExternalServices_table is None:
        return
    try:
        RequestTypeExternalServiceAssociation_table = Table( "request_type_external_service_association", metadata, autoload=True )
    except NoSuchTableError:
        RequestTypeExternalServiceAssociation_table = None
        log.debug( "Failed loading table request_type_external_service_association" )
    # create the 'sequencer_id' column in the 'request_type' table
    try:
        col = Column( "sequencer_id", Integer, ForeignKey( "external_service.id" ), nullable=True )
        col.create( RequestType_table )
        assert col is RequestType_table.c.sequencer_id
    except Exception:
        log.exception("Creating column 'sequencer_id' in the 'request_type' table failed.")
    # populate 'sequencer_id' column in the 'request_type' table from the
    # 'request_type_external_service_association' table
    cmd = "SELECT request_type_id, external_service_id FROM request_type_external_service_association ORDER BY id ASC"
    result = migrate_engine.execute( cmd )
    results_list = result.fetchall()
    # Proceed only if request_types exists
    if len( results_list ):
        for row in results_list:
            request_type_id = row[0]
            external_service_id = row[1]
            cmd = "UPDATE request_type SET sequencer_id=%i WHERE id=%i" % ( external_service_id, request_type_id )
            migrate_engine.execute( cmd )
    # remove the 'request_type_external_service_association' table
    if RequestTypeExternalServiceAssociation_table is not None:
        try:
            RequestTypeExternalServiceAssociation_table.drop()
        except Exception:
            log.exception("Deleting 'request_type_external_service_association' table failed.")
    # rename 'external_service_type_id' column to 'sequencer_type_id' in the table 'external_service'
    # create the column 'sequencer_type_id'
    try:
        col = Column( "sequencer_type_id", TrimmedString( 255 ) )
        col.create( ExternalServices_table )
        assert col is ExternalServices_table.c.sequencer_type_id
    except Exception:
        log.exception("Creating column 'sequencer_type_id' in the 'external_service' table failed.")
    # populate this new column
    cmd = "UPDATE external_service SET sequencer_type_id=external_service_type_id"
    migrate_engine.execute( cmd )
    # remove the 'external_service_type_id' column
    try:
        ExternalServices_table.c.external_service_type_id.drop()
    except Exception:
        log.exception("Deleting column 'external_service_type_id' from the 'external_service' table failed.")
    # rename the 'external_service' table to 'sequencer'
    cmd = "ALTER TABLE external_service RENAME TO sequencer"
    migrate_engine.execute( cmd )
    # if running postgres then rename the primary key sequence too
    if migrate_engine.name in ['postgres', 'postgresql']:
        cmd = "ALTER SEQUENCE external_service_id_seq RENAME TO sequencer_id_seq"
        migrate_engine.execute( cmd )
    # drop the 'external_service_id' column in the 'sample_dataset' table
    try:
        SampleDataset_table = Table( "sample_dataset", metadata, autoload=True )
    except NoSuchTableError:
        SampleDataset_table = None
        log.debug( "Failed loading table 'sample_dataset'" )
    if SampleDataset_table is None:
        return
    try:
        SampleDataset_table.c.external_service_id.drop()
    except Exception:
        log.exception("Deleting column 'external_service_id' from the 'sample_dataset' table failed.")
