"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here. 
"""

import pkg_resources
pkg_resources.require( "psycopg2", "pysqlite>=2", "sqlalchemy>=0.3" )
## pkg_resources.require( "pysqlite>=2", "sqlalchemy>=0.3" )

import sys

from sqlalchemy.ext.sessioncontext import SessionContext
from sqlalchemy.ext.assignmapper import assign_mapper

from sqlalchemy import *
from galaxy.model import *

from cookbook.patterns import Bunch

class TrimmedString( TypeDecorator ):
    impl = String
    def convert_bind_param( self, value, dialect ):
        """Automatically truncate string values"""
        if self.impl.length and value is not None:
            value = value[0:self.impl.length]
        return value
        
metadata = DynamicMetaData( threadlocal=False )
context = SessionContext( create_session ) 

User.table = Table( "galaxy_user", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, PassiveDefault( func.current_timestamp() ) ),
    Column( "update_time", DateTime, PassiveDefault( func.current_timestamp() ), onupdate=func.current_timestamp() ),
 	Column( "email", TrimmedString( 255 ), nullable=False ),
    Column( "password", TrimmedString( 40 ), nullable=False ) )

History.table = Table( "history", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, PassiveDefault( func.current_timestamp() ) ),
    Column( "update_time", DateTime, PassiveDefault( func.current_timestamp() ), onupdate=func.current_timestamp() ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ) ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "hid_counter", Integer, default=1 ),
    Column( "deleted", Boolean ),
    Column( "genome_build", TrimmedString( 40 ) ) )

# model.Query.table = Table( "query", engine,
#             Column( "id", Integer, primary_key=True),
#             Column( "history_id", Integer, ForeignKey( "history.id" ) ),
#             Column( "name", String( 255 ) ),
#             Column( "state", String( 64 ) ),
#             Column( "tool_parameters", Pickle() ) )

Dataset.table = Table( "dataset", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, PassiveDefault( func.current_timestamp() ) ),
    Column( "update_time", DateTime, PassiveDefault( func.current_timestamp() ), onupdate=func.current_timestamp() ),
    Column( "hid", Integer ),
    Column( "history_id", Integer, ForeignKey( "history.id" ) ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "blurb", TrimmedString( 255 ) ),
    Column( "peek" , TEXT ),
    Column( "extension", TrimmedString( 64 ) ),
    Column( "dbkey", TrimmedString( 64 ) ),
    Column( "state", TrimmedString( 64 ) ),
    Column( "metadata", PickleType() ),
    Column( "parent_id", Integer, nullable=True ),
    Column( "designation", TrimmedString( 255 ) ),
    Column( "deleted", Boolean ),
    Column( "purged", Boolean ),
    ForeignKeyConstraint(['parent_id'],['dataset.id'], ondelete="CASCADE") )

ValidationError.table = Table( "validation_error", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ) ),
    Column( "message", TrimmedString( 255 ) ),
    Column( "err_type", TrimmedString( 64 ) ),
    Column( "attributes", TEXT ) )

DatasetChildAssociation.table = Table( "dataset_child_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "parent_dataset_id", Integer, ForeignKey( "dataset.id" ) ),
    Column( "child_dataset_id", Integer, ForeignKey( "dataset.id" ) ),
    Column( "designation", TrimmedString( 255 ) ) )
    
Job.table = Table( "job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, PassiveDefault( func.current_timestamp() ) ),
    Column( "update_time", DateTime, PassiveDefault( func.current_timestamp() ), onupdate=func.current_timestamp() ),
    Column( "history_id", Integer, ForeignKey( "history.id" ) ),
    Column( "tool_id", String( 255 ) ),
    Column( "state", String( 64 ) ),
    Column( "command_line", String() ), 
    Column( "param_filename", String( 1024 ) ),
    Column( "runner_name", String( 255 ) ),
    Column( "stdout", String() ),
    Column( "stderr", String() ),
    Column( "traceback", String() ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), nullable=True ) )
    
JobParameter.table = Table( "job_parameter", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ) ),
    Column( "name", String(255) ),
    Column( "value", String(1024) ) )
    
JobToInputDatasetAssociation.table = Table( "job_to_input_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ) ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ) ),
    Column( "name", String(255) ) )
    
JobToOutputDatasetAssociation.table = Table( "job_to_output_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ) ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ) ),
    Column( "name", String(255) ) )
    
Event.table = Table( "event", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, PassiveDefault( func.current_timestamp() ) ),
    Column( "update_time", DateTime, PassiveDefault( func.current_timestamp() ), onupdate=func.current_timestamp() ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), nullable=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True ),
    Column( "message", TrimmedString( 1024 ) ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), nullable=True ),
    Column( "tool_id", String( 255 ) ) )

GalaxySession.table = Table( "galaxy_session", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, PassiveDefault( func.current_timestamp() ) ),
    Column( "update_time", DateTime, PassiveDefault( func.current_timestamp() ), onupdate=func.current_timestamp() ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True ),
    Column( "remote_host", String( 255 ) ),
    Column( "remote_addr", String( 255 ) ),
    Column( "referer", String( 255 ) ) )

GalaxySessionToHistoryAssociation.table = Table( "galaxy_session_to_history", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, PassiveDefault( func.current_timestamp() ) ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ) ),
    Column( "history_id", Integer, ForeignKey( "history.id" ) ) )

# With the tables defined we can define the mappers and setup the 
# relationships between the model objects.

assign_mapper( context, ValidationError, ValidationError.table )

# assign_mapper( context, Dataset, Dataset.table,
#     properties=dict( children=relation( DatasetChildAssociation, primaryjoin=( DatasetChildAssociation.table.c.parent_dataset_id == Dataset.table.c.id ),
#                                         lazy=False ),
#                      validation_errors=relation( ValidationError, lazy=False ) ) )
                                        
assign_mapper( context, Dataset, Dataset.table,
    properties=dict( 
        children=relation( 
            DatasetChildAssociation, 
            primaryjoin=( DatasetChildAssociation.table.c.parent_dataset_id == Dataset.table.c.id ),
            lazy=False ) ) )
                                        
assign_mapper( context, DatasetChildAssociation, DatasetChildAssociation.table,
    properties=dict( child=relation( Dataset, primaryjoin=( DatasetChildAssociation.table.c.child_dataset_id == Dataset.table.c.id ) ) ) )

# assign_mapper( model.Query, model.Query.table,
#     properties=dict( datasets=relation( model.Dataset.mapper, backref="query") ) )

assign_mapper( context, History, History.table,
    properties=dict( galaxy_sessions=relation( GalaxySessionToHistoryAssociation ),
                     datasets=relation( Dataset, backref="history", order_by=asc(Dataset.table.c.hid) ),
                     active_datasets=relation( Dataset, primaryjoin=( ( Dataset.c.history_id == History.table.c.id ) & ( not_( Dataset.c.deleted ) ) ), order_by=asc( Dataset.table.c.hid ), lazy=False, viewonly=True ) ) )

assign_mapper( context, User, User.table, 
    properties=dict( histories=relation( History, backref="user", 
                                         order_by=desc(History.table.c.update_time) ) ) )

assign_mapper( context, JobToInputDatasetAssociation, JobToInputDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( Dataset ) ) )

assign_mapper( context, JobToOutputDatasetAssociation, JobToOutputDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( Dataset ) ) )

assign_mapper( context, JobParameter, JobParameter.table )

assign_mapper( context, Job, Job.table, 
    properties=dict( galaxy_session=relation( GalaxySession ),
                     history=relation( History ),
                     parameters=relation( JobParameter ),
                     input_datasets=relation( JobToInputDatasetAssociation ),
                     output_datasets=relation( JobToOutputDatasetAssociation ) ) )

assign_mapper( context, Event, Event.table,
    properties=dict( history=relation( History ),
                     galaxy_session=relation( GalaxySession ),
                     user=relation( User.mapper ) ) )

assign_mapper( context, GalaxySession, GalaxySession.table,
    properties=dict( histories=relation( GalaxySessionToHistoryAssociation ),
                     user=relation( User.mapper ) ) )

assign_mapper( context, GalaxySessionToHistoryAssociation, GalaxySessionToHistoryAssociation.table,
    properties=dict( galaxy_session=relation( GalaxySession ), 
                     history=relation( History ) ) )
                     
Dataset.mapper.add_property( "creating_job_associations", relation( JobToOutputDatasetAssociation ) )
    
def db_next_hid( self ):
    """
    Override __next_hid to generate from the database in a concurrency
    safe way.
    """
    conn = self.table.engine.contextual_connect()
    trans = conn.begin()
    try:
        next_hid = select( [self.c.hid_counter], self.c.id == self.id, for_update=True ).scalar()
        self.table.update( self.c.id == self.id ).execute( hid_counter = ( next_hid + 1 ) )
        trans.commit()
        return next_hid
    except:
        trans.rollback()
        raise

History._next_hid = db_next_hid
    
def init( file_path, url, **kwargs ):
    """
    Connect mappings to the database
    """
    create_tables = kwargs.pop( 'create_tables', False )
    # Connect dataset to the file path
    Dataset.file_path = file_path
    # Connect the metadata the database. 
    metadata.connect( url, **kwargs )
    ## metadata.engine.echo = True
    # Create tables if needed
    if create_tables:
        metadata.create_all()
        # metadata.engine.commit()
    # Pack everything into a bunch
    result = Bunch( **globals() )
    result.engine = metadata.engine
    result.flush = lambda *args, **kwargs: context.current.flush( *args, **kwargs )
    result.context = context
    result.create_tables = create_tables
    return result
    
def get_suite():
    """Get unittest suite for this module"""
    import unittest, mapping_tests
    return unittest.makeSuite( mapping_tests.MappingTests )
