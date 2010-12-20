"""
Migration script to populate the 'sequencer' table and it is populated using unique
entries in the 'datatx_info' column in the 'request_type' table. It also deletes the 'datatx_info'
column in the 'request_type' table and adds a foreign key to the 'sequencer' table. The
actual contents of the datatx_info column are stored as form_values. 
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
    
def localtimestamp():
   if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
       return "LOCALTIMESTAMP"
   elif migrate_engine.name == 'sqlite':
       return "current_date || ' ' || current_time"
   else:
       raise Exception( 'Unable to convert data for unknown database type: %s' % db )

def get_latest_id( table ):
    result = db_session.execute( "select id from %s order by id desc" % table )
    row = result.fetchone()
    if row:
        return row[0]
    else:
        raise Exception( 'Unable to get the latest id in the %s table.' % table )
    
def boolean( value ):
   if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
       return value
   elif migrate_engine.name == 'sqlite':
       if value in [ 'True, true' ]:
           return 1
       return 0
   else:
       raise Exception( 'Unable to convert data for unknown database type: %s' % db )

def create_sequencer_form_definition():
    '''
    Create a new form_definition containing 5 fields (host, username, password, 
    data_dir & rename_datasets) which described the existing datatx_info json
    dict in the request_type table 
    '''
    # create new form_definition_current in the db
    cmd = "INSERT INTO form_definition_current VALUES ( %s, %s, %s, %s, %s )"
    cmd = cmd % ( nextval( 'form_definition_current' ),
                  localtimestamp(),
                  localtimestamp(),
                  'NULL',
                  boolean( 'false' ) )
    db_session.execute( cmd )
    # get this form_definition_current id
    form_definition_current_id = get_latest_id( 'form_definition_current' )
    # create new form_definition in the db
    form_definition_name = 'Generic sequencer form'
    form_definition_desc = ''
    form_definition_fields = []
    fields = [ ( 'Host', 'TextField' ), 
               ( 'User name', 'TextField' ),
               ( 'Password', 'PasswordField' ),
               ( 'Data directory', 'TextField' ) ]
    for index, ( label, field_type ) in enumerate( fields ):
        form_definition_fields.append( { 'name': 'field_%i' % index,
                                         'label': label, 
                                         'helptext': '', 
                                         'visible': True,
                                         'required': False,
                                         'type': field_type,
                                         'selectlist': [],
                                         'layout': 'none',
                                         'default': '' } )
    form_definition_fields.append( { 'name': 'field_%i' % len( fields ),
                                     'label': 'Prepend the experiment name and sample name to the dataset name?', 
                                     'helptext': 'Galaxy datasets are renamed by prepending the experiment name and sample name to the dataset name, ensuring dataset names remain unique in Galaxy even when multiple datasets have the same name on the sequencer.', 
                                     'visible': True,
                                     'required': False,
                                     'type': 'SelectField',
                                     'selectlist': [ 'Do not rename',
                                                     'Preprend sample name',
                                                     'Prepend experiment name',
                                                     'Prepend experiment and sample name' ],
                                     'layout': 'none',
                                     'default': '' } )
    form_definition_type = 'Sequencer Information Form'
    form_definition_layout = to_json_string('[]')
    cmd = "INSERT INTO form_definition VALUES ( %s, %s, %s, '%s', '%s', %s, '%s', '%s', '%s' )"
    cmd = cmd % ( nextval( 'form_definition' ),
                  localtimestamp(),
                  localtimestamp(),
                  form_definition_name,
                  form_definition_desc,
                  form_definition_current_id,
                  to_json_string( form_definition_fields ),
                  form_definition_type,
                  form_definition_layout )
    db_session.execute( cmd )
    # get this form_definition id
    form_definition_id = get_latest_id( 'form_definition' )
    # update the form_definition_id column in form_definition_current
    cmd = "UPDATE form_definition_current SET latest_form_id=%i WHERE id=%i" %( form_definition_id, form_definition_current_id )
    db_session.execute( cmd )
    return form_definition_id

def get_sequencer_id( sequencer_info ):
    '''Get the sequencer id corresponding to the sequencer information'''
    # Check if there is any existing sequencer which have the same sequencer
    # information fields & values
    cmd = "SELECT sequencer.id, form_values.content FROM sequencer, form_values WHERE sequencer.form_values_id=form_values.id"
    result = db_session.execute( cmd )
    for row in result:
        sequencer_id = row[0]
        values = str( row[1] )
        if not values.strip():
            continue
        values = from_json_string( values )
        # proceed only if sequencer_info is a valid list
        if values and type( values ) == type( dict() ):
            if sequencer_info.get( 'host', '' ) == values.get( 'field_0', '' ) \
               and sequencer_info.get( 'username', '' ) == values.get( 'field_1', '' ) \
               and sequencer_info.get( 'password', '' ) == values.get( 'field_2', '' ) \
               and sequencer_info.get( 'data_dir', '' ) == values.get( 'field_3', '' ) \
               and sequencer_info.get( 'rename_dataset', '' ) == values.get( 'field_4', '' ):
                return sequencer_id
    return None

def add_sequencer( sequencer_index, sequencer_form_definition_id, sequencer_info ):
    '''Adds a new sequencer to the sequencer table along with its form values.'''
    # Create a new form values record with the supplied sequencer information
    values = to_json_string( { 'field_0': sequencer_info.get( 'host', '' ),
                               'field_1': sequencer_info.get( 'username', '' ),
                               'field_2': sequencer_info.get( 'password', '' ),
                               'field_3': sequencer_info.get( 'data_dir', '' ),
                               'field_4': sequencer_info.get( 'rename_dataset', '' ) } )
    cmd = "INSERT INTO form_values VALUES ( %s, %s, %s, %s, '%s' )" % ( nextval( 'form_values' ), 
                                                                        localtimestamp(), 
                                                                        localtimestamp(), 
                                                                        sequencer_form_definition_id,
                                                                        values )
    db_session.execute(cmd)
    sequencer_form_values_id = get_latest_id( 'form_values' )
    # Create a new sequencer record with reference to the form value created above.
    name = 'Sequencer_%i' % sequencer_index
    desc = ''
    version = ''
    result_datasets = dict()
    sequencer_type_id = 'simple_unknown_sequencer'
    cmd = "INSERT INTO sequencer VALUES ( %s, %s, %s, '%s', '%s', '%s', '%s', %s, %s, %s )"
    cmd = cmd % ( nextval('sequencer'), 
                  localtimestamp(), 
                  localtimestamp(), 
                  name, 
                  desc, 
                  sequencer_type_id,
                  version, 
                  sequencer_form_definition_id,
                  sequencer_form_values_id,
                  boolean( 'false' ) )
    db_session.execute(cmd)
    return get_latest_id( 'sequencer' )

def update_sequencer_id_in_request_type( request_type_id, sequencer_id ):
    '''Update the foreign key to the sequencer table in the request_type table'''
    cmd = "UPDATE request_type SET sequencer_id=%i WHERE id=%i" %( sequencer_id, request_type_id )
    db_session.execute( cmd )
    
def upgrade():
    print __doc__
    metadata.reflect()
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
    except NoSuchTableError, e:
        RequestType_table = None
        log.debug( "Failed loading table 'request_type'" )
    if not RequestType_table:
        return
    # load the sequencer table
    try:
        Sequencer_table = Table( "sequencer", metadata, autoload=True )
    except NoSuchTableError, e:
        Sequencer_table = None
        log.debug( "Failed loading table 'sequencer'" )
    if not Sequencer_table:
        return
    # create foreign key field to the sequencer table in the request_type table
    try:
        col = Column( "sequencer_id", Integer, ForeignKey( "sequencer.id" ), nullable=True, index=True )
        col.create( RequestType_table )
        assert col is RequestType_table.c.sequencer_id
    except Exception, e:
        log.debug( "Creating column 'sequencer_id' in the 'request_type' table failed: %s" % ( str( e ) ) )   
    # copy the sequencer information contained in the 'datatx_info' column 
    # of the request_type table to the form values referenced in the sequencer table
    cmd = "SELECT id, name, datatx_info FROM request_type ORDER BY id ASC"
    result = db_session.execute( cmd )
    results_list = result.fetchall()
    # Proceed only if request_types exists
    if len( results_list ):
        # In this migration script the all the contents of the datatx_info are stored as form_values   
        # with a pointer to the sequencer table. This way the sequencer information can be customized  
        # by the admin and is no longer restricted to host, username, password, data directory.
        # For the existing request_types in the database, we add a new form_definition 
        # with these 4 fields. Then we populate the sequencer table with unique datatx_info 
        # column from the existing request_types.
        sequencer_form_definition_id = create_sequencer_form_definition()
        sequencer_index = 1
        for row in results_list:
            request_type_id = row[0]
            request_type_name = row[1]
            sequencer_info = str( row[2] ) # datatx_info column
            # skip if sequencer_info is empty
            if not sequencer_info.strip() or sequencer_info in ['None', 'null']:
                continue
            sequencer_info = from_json_string( sequencer_info.strip() )
            # proceed only if sequencer_info is a valid dict
            if sequencer_info and type( sequencer_info ) == type( dict() ):
                # check if this sequencer has already been added to the sequencer table
                sequencer_id = get_sequencer_id( sequencer_info )
                if not sequencer_id:
                    # add to the sequencer table
                    sequencer_id = add_sequencer( sequencer_index, sequencer_form_definition_id, sequencer_info )
                # now update the sequencer_id column in request_type table
                update_sequencer_id_in_request_type( request_type_id, sequencer_id )
                sequencer_index = sequencer_index + 1
                
    # Finally delete the 'datatx_info' column from the request_type table
    try:
        RequestType_table.c.datatx_info.drop()
    except Exception, e:
        log.debug( "Deleting column 'datatx_info' in the 'request_type' table failed: %s" % ( str( e ) ) )   
        
        
def downgrade():
    metadata.reflect()
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
    except NoSuchTableError, e:
        RequestType_table = None
        log.debug( "Failed loading table 'request_type'" )
    if RequestType_table:
        # create the 'datatx_info' column
        try:
            col = Column( "datatx_info", JSONType() )
            col.create( RequestType_table )
            assert col is RequestType_table.c.datatx_info
        except Exception, e:
            log.debug( "Creating column 'datatx_info' in the 'request_type' table failed: %s" % ( str( e ) ) )   
        # restore the datatx_info column data in the request_type table with data from 
        # the sequencer and the form_values table
        cmd = "SELECT request_type.id, form_values.content "\
              + " FROM request_type, sequencer, form_values "\
              + " WHERE request_type.sequencer_id=sequencer.id AND sequencer.form_values_id=form_values.id "\
              + " ORDER  BY request_type.id ASC"
        result = db_session.execute( cmd )
        for row in result:
            request_type_id = row[0]
            seq_values = from_json_string( str( row[1] ) ) 
            # create the datatx_info json dict
            datatx_info = to_json_string( dict( host = seq_values.get( 'field_0', '' ),
                                                username = seq_values.get( 'field_1', '' ),
                                                password = seq_values.get( 'field_2', '' ),
                                                data_dir = seq_values.get( 'field_3', '' ),
                                                rename_dataset = seq_values.get( 'field_4', '' ) ) )
            # update the column
            cmd = "UPDATE request_type SET datatx_info='%s' WHERE id=%i" %( datatx_info, request_type_id )
            db_session.execute( cmd )
        # delete foreign key field to the sequencer table in the request_type table
        try:
            RequestType_table.c.sequencer_id.drop()
        except Exception, e:
            log.debug( "Deleting column 'sequencer_id' in the 'request_type' table failed: %s" % ( str( e ) ) )   

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
