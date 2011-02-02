"""
This migration script renames the sequencer table to 'external_service' table and 
creates a association table, 'request_type_external_service_association' and 
populates it. The 'sequencer_id' foreign_key from the 'request_type' table is removed.
The 'sequencer_type_id' column is renamed to 'external_service_type_id' in the renamed
table 'external_service'. Finally, adds a foreign key to the external_service table in the 
sample_dataset table and populates it.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from sqlalchemy.exc import *

from galaxy.model.custom_types import *

from galaxy.util.json import from_json_string, to_json_string

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def nextval( table, col='id' ):
    if migrate_engine.name == 'postgres':
        return "nextval('%s_%s_seq')" % ( table, col )
    elif migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
        return "null"
    else:
        raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )
    
    
def upgrade():
    print __doc__
    # Load existing tables
    metadata.reflect()
    # add a foreign key to the external_service table in the sample_dataset table
    try:
        SampleDataset_table = Table( "sample_dataset", metadata, autoload=True )
    except NoSuchTableError, e:
        SampleDataset_table = None
        log.debug( "Failed loading table 'sample_dataset'" )
    if not SampleDataset_table:
        return
    try:
        Sequencer_table = Table( "sequencer", metadata, autoload=True )
    except NoSuchTableError, e:
        Sequencer_table = None
        log.debug( "Failed loading table 'sequencer'" )
    if not Sequencer_table:
        return
    # create the column. Call it external_services_id as the table 'sequencer' is 
    # going to be renamed to 'external_service'  
    try:
        col = Column( "external_service_id", Integer, index=True )
        col.create( SampleDataset_table )
        assert col is SampleDataset_table.c.external_service_id
    except Exception, e:
        log.debug( "Creating column 'external_service_id' in the 'sample_dataset' table failed: %s" % ( str( e ) ) )
    # Add the foreign key constraint
    try:
        cons = ForeignKeyConstraint( [SampleDataset_table.c.external_service_id],
                                     [Sequencer_table.c.id],
                                     name='sample_dataset_external_services_id_fk' )
        # Create the constraint
        cons.create()
    except Exception, e:
        log.debug( "Adding foreign key constraint 'sample_dataset_external_services_id_fk' to table 'sample_dataset' failed: %s" % ( str( e ) ) )
    # populate the column
    cmd = "SELECT sample_dataset.id, request_type.sequencer_id " \
          + " FROM sample_dataset, sample, request, request_type " \
          + " WHERE sample.id=sample_dataset.sample_id and request.id=sample.request_id and request.request_type_id=request_type.id " \
          + " ORDER BY sample_dataset.id"
    result = db_session.execute( cmd )
    for r in result:
        sample_dataset_id = int(r[0])
        sequencer_id = int(r[1])
        cmd = "UPDATE sample_dataset SET external_service_id='%i' where id=%i" % ( sequencer_id, sample_dataset_id )
        db_session.execute( cmd )
    # load request_type table
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
    except NoSuchTableError:
        RequestType_table = None
        log.debug( "Failed loading table request_type" )
    if not RequestType_table:
        return 
    # rename 'sequencer' table to 'external_service'
    cmd = "ALTER TABLE sequencer RENAME TO external_service" 
    db_session.execute( cmd )
    try:
        ExternalServices_table = Table( "external_service", metadata, autoload=True )
    except NoSuchTableError, e:
        ExternalServices_table = None
        log.debug( "Failed loading table 'external_service'" )
    if not ExternalServices_table:
        return
    # if running postgres then rename the primary key sequence too
    if migrate_engine.name == 'postgres':
        cmd = "ALTER TABLE sequencer_id_seq RENAME TO external_service_id_seq" 
        db_session.execute( cmd )
    # rename 'sequencer_type_id' column to 'external_service_type_id' in the table 'external_service'
    # create the column as 'external_service_type_id'
    try:
        col = Column( "external_service_type_id", TrimmedString( 255 ) )
        col.create( ExternalServices_table )
        assert col is ExternalServices_table.c.external_service_type_id
    except Exception, e:
        log.debug( "Creating column 'external_service_type_id' in the 'external_service' table failed: %s" % ( str( e ) ) )
    # populate this new column
    cmd = "UPDATE external_service SET external_service_type_id=sequencer_type_id"
    db_session.execute( cmd )
    # remove the 'sequencer_type_id' column
    try:
        ExternalServices_table.c.sequencer_type_id.drop()
    except Exception, e:
        log.debug( "Deleting column 'sequencer_type_id' from the 'external_service' table failed: %s" % ( str( e ) ) )
    # create 'request_type_external_service_association' table
    RequestTypeExternalServiceAssociation_table = Table( "request_type_external_service_association", metadata,
                                                         Column( "id", Integer, primary_key=True ),
                                                         Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ),
                                                         Column( "external_service_id", Integer, ForeignKey( "external_service.id" ), index=True ) )
    try:
        RequestTypeExternalServiceAssociation_table.create()
    except Exception, e:
        log.debug( "Creating request_type_external_service_association table failed: %s" % str( e ) )
    try:
        RequestTypeExternalServiceAssociation_table = Table( "request_type_external_service_association", metadata, autoload=True )
    except NoSuchTableError:
        RequestTypeExternalServiceAssociation_table = None
        log.debug( "Failed loading table request_type_external_service_association" )  
    if not RequestTypeExternalServiceAssociation_table:
        return
    # populate 'request_type_external_service_association' table
    cmd = "SELECT id, sequencer_id FROM request_type ORDER BY id ASC"
    result = db_session.execute( cmd )
    results_list = result.fetchall()
    # Proceed only if request_types exists
    if len( results_list ):
        for row in results_list:
            request_type_id = row[0]
            sequencer_id = row[1]
            if not sequencer_id:
                sequencer_id = 'null'
            cmd = "INSERT INTO request_type_external_service_association VALUES ( %s, %s, %s )"
            cmd = cmd % ( nextval( 'request_type_external_service_association' ),
                          request_type_id,
                          sequencer_id )
            db_session.execute( cmd )
    # drop the 'sequencer_id' column in the 'request_type' table
    # sqlite does not support dropping columns
    if migrate_engine.name == 'sqlite':
        # In sqlite, create a temp table without the column that needs to be removed.
        # then copy all the rows from the original table and finally rename the temp table
        RequestTypeTemp_table = Table( 'request_type_temp', metadata,
                                        Column( "id", Integer, primary_key=True),
                                        Column( "create_time", DateTime, default=now ),
                                        Column( "update_time", DateTime, default=now, onupdate=now ),
                                        Column( "name", TrimmedString( 255 ), nullable=False ),
                                        Column( "desc", TEXT ),
                                        Column( "request_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
                                        Column( "sample_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
                                        Column( "deleted", Boolean, index=True, default=False ) )
        try:
            RequestTypeTemp_table.create()
        except Exception, e:
            log.debug( "Creating request_type_temp table failed: %s" % str( e ) )  
        # insert all the rows from the request table to the request_temp table
        cmd = \
            "INSERT INTO request_type_temp " + \
            "SELECT id," + \
                "create_time," + \
                "update_time," + \
                "name," + \
                "desc," + \
                "request_form_id," + \
                "sample_form_id," + \
                "deleted " + \
            "FROM request_type;" 
        db_session.execute( cmd )
        # delete the 'request_type' table
        try:
            RequestType_table.drop()
        except Exception, e:
            log.debug( "Dropping request_type table failed: %s" % str( e ) )
        # rename table request_temp to request
        cmd = "ALTER TABLE request_type_temp RENAME TO request_type" 
        db_session.execute( cmd )
    else:
        try:
            RequestType_table.c.sequencer_id.drop()
        except Exception, e:
            log.debug( "Deleting column 'sequencer_id' from the 'request_type' table failed: %s" % ( str( e ) ) )


def downgrade():
    # Load existing tables
    metadata.reflect()
    # load sequencer & request_type table
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
    except NoSuchTableError:
        RequestType_table = None
        log.debug( "Failed loading table request_type" )
    if not RequestType_table:
        return 
    try:
        ExternalServices_table = Table( "external_service", metadata, autoload=True )
    except NoSuchTableError, e:
        ExternalServices_table = None
        log.debug( "Failed loading table 'external_service'" )
    if not ExternalServices_table:
        return
    try:
        RequestTypeExternalServiceAssociation_table = Table( "request_type_external_service_association", metadata, autoload=True )
    except NoSuchTableError:
        RequestTypeExternalServiceAssociation_table = None
        log.debug( "Failed loading table request_type_external_service_association" )  
    # create the 'sequencer_id' column in the 'request_type' table
    try:
        col = Column( "sequencer_id", Integer, ForeignKey( "external_service.id" ), nullable=True, index=True )
        col.create( RequestType_table )
        assert col is RequestType_table.c.sequencer_id
    except Exception, e:
        log.debug( "Creating column 'sequencer_id' in the 'request_type' table failed: %s" % ( str( e ) ) )   
    # populate 'sequencer_id' column in the 'request_type' table from the 
    # 'request_type_external_service_association' table
    cmd = "SELECT request_type_id, external_service_id FROM request_type_external_service_association ORDER BY id ASC"
    result = db_session.execute( cmd )
    results_list = result.fetchall()
    # Proceed only if request_types exists
    if len( results_list ):
        for row in results_list:
            request_type_id = row[0]
            external_service_id = row[1]
            cmd = "UPDATE request_type SET sequencer_id=%i WHERE id=%i" % ( external_service_id, request_type_id )
            db_session.execute( cmd )
    # remove the 'request_type_external_service_association' table
    if RequestTypeExternalServiceAssociation_table:
        try:
            RequestTypeExternalServiceAssociation_table.drop()
        except Exception, e:
            log.debug( "Deleting 'request_type_external_service_association' table failed: %s" % str( e ) )
    # rename 'external_service_type_id' column to 'sequencer_type_id' in the table 'external_service'
    # create the column 'sequencer_type_id'
    try:
        col = Column( "sequencer_type_id", TrimmedString( 255 ) )
        col.create( ExternalServices_table )
        assert col is ExternalServices_table.c.sequencer_type_id
    except Exception, e:
        log.debug( "Creating column 'sequencer_type_id' in the 'external_service' table failed: %s" % ( str( e ) ) )   
    # populate this new column
    cmd = "UPDATE external_service SET sequencer_type_id=external_service_type_id"
    db_session.execute( cmd )
    # remove the 'external_service_type_id' column
    try:
        ExternalServices_table.c.external_service_type_id.drop()
    except Exception, e:
        log.debug( "Deleting column 'external_service_type_id' from the 'external_service' table failed: %s" % ( str( e ) ) )
    # rename the 'external_service' table to 'sequencer'
    cmd = "ALTER TABLE external_service RENAME TO sequencer" 
    db_session.execute( cmd )
    # if running postgres then rename the primary key sequence too
    if migrate_engine.name == 'postgres':
        cmd = "ALTER SEQUENCE external_service_id_seq RENAME TO sequencer_id_seq" 
        db_session.execute( cmd )
    # drop the 'external_service_id' column in the 'sample_dataset' table
    try:
        SampleDataset_table = Table( "sample_dataset", metadata, autoload=True )
    except NoSuchTableError, e:
        SampleDataset_table = None
        log.debug( "Failed loading table 'sample_dataset'" )
    if not SampleDataset_table:
        return
    try:
        SampleDataset_table.c.external_service_id.drop()
    except Exception, e:
        log.debug( "Deleting column 'external_service_id' from the 'sample_dataset' table failed: %s" % ( str( e ) ) )   


    
