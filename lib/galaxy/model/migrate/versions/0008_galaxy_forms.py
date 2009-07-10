from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exceptions import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, transactional=False ) )


FormDefinitionCurrent_table = Table('form_definition_current', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "latest_form_id", Integer, 
            #ForeignKey( "form_definition.id", use_alter=True, name='form_definition_current_latest_form_id_fk'), 
            index=True ),
    Column( "deleted", Boolean, index=True, default=False ))
FormDefinition_table = Table('form_definition', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "form_definition_current_id", Integer, ForeignKey( "form_definition_current.id" ), index=True, nullable=False ),
    Column( "fields", JSONType()) )

FormValues_table = Table('form_values', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "content", JSONType()) )

RequestType_table = Table('request_type', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "request_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "sample_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ) )
# request table
Request_table = Table('request', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

Sample_table = Table('sample', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "request_id", Integer, ForeignKey( "request.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False )  )

SampleState_table = Table('sample_state', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ) )

SampleEvent_table = Table('sample_event', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "sample_id", Integer, ForeignKey( "sample.id" ), index=True ), 
    Column( "sample_state_id", Integer, ForeignKey( "sample_state.id" ), index=True ),
    Column( "comment", TEXT ) )




def upgrade():
    # Load existing tables
    metadata.reflect()
    
    # Add all of the new tables above
#    metadata.create_all()
    try:
        FormDefinitionCurrent_table.create()
    except Exception, e:
        log.debug( "Creating form_definition_current table failed: %s" % str( e ) ) 
    try:
        FormDefinition_table.create()
    except Exception, e:
        log.debug( "Creating form_definition table failed: %s" % str( e ) )
    # Add 1 foreign key constraint to the form_definition_current table
    if FormDefinitionCurrent_table and FormDefinition_table:
        try:
            cons = ForeignKeyConstraint( [FormDefinitionCurrent_table.c.latest_form_id],
                                         [FormDefinition_table.c.id],
                                         name='form_definition_current_latest_form_id_fk' )
            # Create the constraint
            cons.create()
        except Exception, e:
            log.debug( "Adding foreign key constraint 'form_definition_current_latest_form_id_fk' to table 'form_definition_current' failed: %s" % ( str( e ) ) )
    try:
        FormValues_table.create()
    except Exception, e:
        log.debug( "Creating form_values table failed: %s" % str( e ) )  
    try:
        RequestType_table.create()
    except Exception, e:
        log.debug( "Creating request_type table failed: %s" % str( e ) )  
    try:
        Request_table.create()
    except Exception, e:
        log.debug( "Creating request table failed: %s" % str( e ) )  
    try:
        Sample_table.create()
    except Exception, e:
        log.debug( "Creating sample table failed: %s" % str( e ) )  
    try:
        SampleState_table.create()
    except Exception, e:
        log.debug( "Creating sample_state table failed: %s" % str( e ) )  
    try:
        SampleEvent_table.create()
    except Exception, e:
        log.debug( "Creating sample_event table failed: %s" % str( e ) )  
    
 

def downgrade():
    # Load existing tables
    metadata.reflect()
    try:
        FormDefinition_table.drop()
    except Exception, e:
        log.debug( "Dropping form_definition table failed: %s" % str( e ) )  
    try:
        FormDefinitionCurrent_table.drop()
    except Exception, e:
        log.debug( "Dropping form_definition_current table failed: %s" % str( e ) )  
    try:
        FormValues_table.drop()
    except Exception, e:
        log.debug( "Dropping form_values table failed: %s" % str( e ) )  
    try:
        Request_table.drop()
    except Exception, e:
        log.debug( "Dropping request table failed: %s" % str( e ) )  
    try:
        RequestType_table.drop()
    except Exception, e:
        log.debug( "Dropping request_type table failed: %s" % str( e ) )  
    try:
        Sample_table.drop()
    except Exception, e:
        log.debug( "Dropping sample table failed: %s" % str( e ) )  
    try:
        SampleState_table.drop()
    except Exception, e:
        log.debug( "Dropping sample_state table failed: %s" % str( e ) )  
    try:
        SampleEvent_table.drop()
    except Exception, e:
        log.debug( "Dropping sample_event table failed: %s" % str( e ) )      
        
        
        
          
