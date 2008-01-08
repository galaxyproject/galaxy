"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here. 
"""
import logging
log = logging.getLogger( __name__ )

import pkg_resources
pkg_resources.require( "pysqlite>=2", "sqlalchemy>=0.3" )

# Attempt to load psycopg but fail quietly since it may not be in an egg 
# or even needed.
try: pkg_resources.require( "psycopg2" )
except: pass

import sys
import datetime

from sqlalchemy.ext.sessioncontext import SessionContext
from sqlalchemy.ext.assignmapper import assign_mapper

from sqlalchemy import *
from galaxy.model import *
from galaxy.model.custom_types import *
from galaxy.util.bunch import Bunch

metadata = DynamicMetaData( threadlocal=False )
context = SessionContext( create_session ) 

# NOTE REGARDING TIMESTAMPS:
#   It is currently difficult to have the timestamps calculated by the 
#   database in a portable way, so we're doing it in the client. This
#   also saves us from needing to postfetch on postgres. HOWEVER: it
#   relies on the client's clock being set correctly, so if clustering
#   web servers, use a time server to ensure synchronization

# Return the current time in UTC without any timezone information
now = datetime.datetime.utcnow

User.table = Table( "galaxy_user", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "email", TrimmedString( 255 ), nullable=False ),
    Column( "password", TrimmedString( 40 ), nullable=False ) )

History.table = Table( "history", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
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
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "hid", Integer ),
    Column( "history_id", Integer, ForeignKey( "history.id" ) ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "blurb", TrimmedString( 255 ) ),
    Column( "peek" , TEXT ),
    Column( "extension", TrimmedString( 64 ) ),
    Column( "dbkey", TrimmedString( 64 ), key="old_dbkey" ), # maps to old_dbkey, see __init__.py
    Column( "state", TrimmedString( 64 ) ),
    Column( "metadata", MetadataType(), key="_metadata" ),
    Column( "parent_id", Integer, nullable=True ),
    Column( "designation", TrimmedString( 255 ) ),
    Column( "deleted", Boolean ),
    Column( "purged", Boolean ),
    Column( "visible", Boolean ),
    Column( "filename_id", Integer, ForeignKey( "dataset_filename.id" ), nullable=True ),
    Column( 'file_size', Numeric( 15, 0 ) ),
    ForeignKeyConstraint(['parent_id'],['dataset.id'], ondelete="CASCADE") )

DatasetFileName.table = Table( "dataset_filename", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "filename", TEXT ),
    Column( "extra_files_path", TEXT, nullable=True, default=None ),
    Column( "readonly", Boolean, default=False ) )

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
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
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
    Column( "value", TEXT ) )
    
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
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), nullable=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True ),
    Column( "message", TrimmedString( 1024 ) ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), nullable=True ),
    Column( "tool_id", String( 255 ) ) )

GalaxySession.table = Table( "galaxy_session", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True ),
    Column( "remote_host", String( 255 ) ),
    Column( "remote_addr", String( 255 ) ),
    Column( "referer", TEXT ) )

GalaxySessionToHistoryAssociation.table = Table( "galaxy_session_to_history", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ) ),
    Column( "history_id", Integer, ForeignKey( "history.id" ) ) )

StoredWorkflow.table = Table( "stored_workflow", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=False ),
    Column( "encoded_value", String )
    )

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
            lazy=False,
            backref="parent" ),
        dataset_file=relation( 
            DatasetFileName, 
            primaryjoin=( DatasetFileName.table.c.id == Dataset.table.c.filename_id ) )
            ) )

assign_mapper( context, DatasetFileName, DatasetFileName.table )

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

assign_mapper( context, StoredWorkflow, StoredWorkflow.table,
    properties=dict( user=relation( User.mapper ) ) )
                     
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
    """Connect mappings to the database"""
    create_tables = kwargs.pop( 'create_tables', False )
    # Connect dataset to the file path
    Dataset.file_path = file_path
    # MySQL hacking, doesn't support passive defaults for anything but TIMESTAMP
    if url.startswith( "mysql" ):
        for table in metadata.tables.values():
            if table.columns.has_key( "create_time" ):
                table.columns['create_time'].type = TIMESTAMP()
            if table.columns.has_key( "update_time" ):
                table.columns['update_time'].type = TIMESTAMP()
        metadata.connect( url, **kwargs )
    # Connect the metadata to the database. 
    elif url.startswith( "postgresql:///" ): 
        import psycopg
        try:
            dbconn = url.split('///')
            dbtype = dbconn[0]
            dbname = dbconn[1]
            def connect():
                connection = psycopg.connect( 'dbname=%s' %dbname )
                connection.set_isolation_level(1)
                return connection
            engine = create_engine('%s///' %dbtype, creator=connect)
            metadata.connect( engine )
        except:
            log.exception( "error connecting to database using connection: '%s'." % url )
            metadata.connect( url, **kwargs )
    else:
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
