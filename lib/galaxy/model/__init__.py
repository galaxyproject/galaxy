"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""

import os.path, os, errno
import sha
import galaxy.datatypes
from galaxy.util.bunch import Bunch
from galaxy import util
import tempfile
import galaxy.datatypes.registry
from galaxy.datatypes.metadata import MetadataCollection

import logging
log = logging.getLogger( __name__ )

datatypes_registry = galaxy.datatypes.registry.Registry() #Default Value Required for unit tests

def set_datatypes_registry( d_registry ):
    """
    Set up datatypes_registry
    """
    global datatypes_registry
    datatypes_registry = d_registry

class User( object ):
    def __init__( self, email=None, password=None ):
        self.email = email
        self.password = password
        # Relationships
        self.histories = []
    def set_password_cleartext( self, cleartext ):
        """Set 'self.password' to the digest of 'cleartext'."""
        self.password = sha.new( cleartext ).hexdigest()
    def check_password( self, cleartext ):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == sha.new( cleartext ).hexdigest()
        
class Job( object ):
    """
    A job represents a request to run a tool given input datasets, tool 
    parameters, and output datasets.
    """
    states = Bunch( NEW = 'new',
                    WAITING = 'waiting',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    ERROR = 'error',
                    DELETED = 'deleted' )
    def __init__( self ):
        self.session_id = None
        self.tool_id = None
        self.tool_version = None
        self.command_line = None
        self.param_filename = None
        self.parameters = []
        self.input_datasets = []
        self.output_datasets = []
        self.state = Job.states.NEW
        self.info = None
        self.job_runner_name = None
        self.job_runner_external_id = None
    def add_parameter( self, name, value ):
        self.parameters.append( JobParameter( name, value ) )
    def add_input_dataset( self, name, dataset ):
        self.input_datasets.append( JobToInputDatasetAssociation( name, dataset ) )
    def add_output_dataset( self, name, dataset ):
        self.output_datasets.append( JobToOutputDatasetAssociation( name, dataset ) )
    def set_state( self, state ):
        self.state = state
        # For historical reasons state propogates down to datasets
        for da in self.output_datasets:
            da.dataset.state = state
    def get_param_values( self, app ):
        """
        Read encoded parameter values from the database and turn back into a
        dict of tool parameter values.
        """
        param_dict = dict( [ ( p.name, p.value ) for p in self.parameters ] )
        tool = app.toolbox.tools_by_id[self.tool_id]
        param_dict = tool.params_from_strings( param_dict, app )
        return param_dict
                
class JobParameter( object ):
    def __init__( self, name, value ):
        self.name = name
        self.value = value
          
class JobToInputDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset
        
class JobToOutputDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset
        
class History( object ):
    def __init__( self, id=None, name=None, user=None ):
        self.id = id
        self.name = name or "Unnamed history"
        self.deleted = False
        self.purged = False
        self.genome_build = None
        # Relationships
        self.user = user
        self.datasets = []
        self.galaxy_sessions = []
        
    def _next_hid( self ):
        # TODO: override this with something in the database that ensures 
        # better integrity
        if len( self.datasets ) == 0:
            return 1
        else:
            last_hid = 0
            for dataset in self.datasets:
                if dataset.hid > last_hid:
                    last_hid = dataset.hid
            return last_hid + 1

    def add_galaxy_session( self, galaxy_session, association=None ):
        if association is None:
            self.galaxy_sessions.append( GalaxySessionToHistoryAssociation( galaxy_session, self ) )
        else:
            self.galaxy_sessions.append( association )

    def add_dataset( self, dataset, parent_id=None, genome_build=None, set_hid = True ):
        if parent_id:
            for data in self.datasets:
                if data.id == parent_id:
                    dataset.hid = data.hid
                    break
            else:
                if set_hid: dataset.hid = self._next_hid()
        else:
            if set_hid: dataset.hid = self._next_hid()
        self.genome_build = genome_build
        self.datasets.append( dataset )

    def copy(self):
        des = History()
        des.flush()
        des.name = self.name
        des.user_id = self.user_id
        for data in self.datasets:
            new_data = data.copy()
            des.add_dataset(new_data)
            new_data.hid = data.hid
            new_data.flush()
            for child_assoc in data.children:
                new_child = child_assoc.child.copy()
                new_assoc = DatasetChildAssociation( child_assoc.designation )
                new_assoc.child = new_child
                new_assoc.parent = new_data
                new_child.flush()
        des.hid_counter = self.hid_counter
        des.flush()
        return des

# class Query( object ):
#     def __init__( self, name=None, state=None, tool_parameters=None, history=None ):
#         self.name = name or "Unnamed query"
#         self.state = state
#         self.tool_parameters = tool_parameters
#         # Relationships
#         self.history = history
#         self.datasets = []

class Dataset( object ):
    states = Bunch( NEW = 'new',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    EMPTY = 'empty',
                    ERROR = 'error',
                    DELETED = 'deleted')
    file_path = "/tmp/"
    engine = None
    def __init__( self, id=None, hid=None, name=None, info=None, blurb=None, peek=None, extension=None, 
                  dbkey=None, state=None, metadata=None, history=None, parent_id=None, designation=None,
                  validation_errors=None, visible=True, filename_id = None, file_size=None ):
        self.name = name or "Unnamed dataset"
        self.id = id
        self.hid = hid
        self.info = info
        self.blurb = blurb
        self.peek = peek
        self.extension = extension
        self.dbkey = dbkey
        self.state = state
        self._metadata = metadata or dict()
        self.parent_id = parent_id
        self.designation = designation
        self.deleted = False
        self.purged = False
        self.visible = visible
        self.filename_id = filename_id
        self.file_size = file_size
        # Relationships
        self.history = history
        self.validation_errors = validation_errors
        
    @property
    def ext( self ):
        return self.extension
    
    def get_file_name( self ):
        if self.filename_id is None:
            assert self.id is not None, "ID must be set before filename used (commit the object)"
            # First try filename directly under file_path
            filename = os.path.join( self.file_path, "dataset_%d.dat" % self.id )
            # Only use that filename if it already exists (backward compatibility),
            # otherwise construct hashed path
            if not os.path.exists( filename ):
                dir = os.path.join( self.file_path, *directory_hash_id( self.id ) )
                # Create directory if it does not exist
                try:
                    os.makedirs( dir )
                except OSError, e:
                    # File Exists is okay, otherwise reraise
                    if e.errno != errno.EEXIST:
                        raise
                # Return filename inside hashed directory
                return os.path.abspath( os.path.join( dir, "dataset_%d.dat" % self.id ) )
        else:
            filename = self.dataset_file.filename
        # Make filename absolute
        return os.path.abspath( filename )
            
    def set_file_name (self, filename):
        if filename is None:
            self.filename_id = None
        else:
            filename_obj = DatasetFileName.get_by(filename=filename)
            if filename_obj is None:
                filename_obj = DatasetFileName(filename=filename, extra_files_path=self.extra_files_path)
                filename_obj.flush()
            self.filename_id = filename_obj.id
        self.flush()
        self.refresh()
        
    file_name = property( get_file_name, set_file_name )
    
    @property
    def extra_files_path( self ):
        if self.dataset_file and self.dataset_file.extra_files_path: 
            path = self.dataset_file.extra_files_path
        else:
            path = os.path.join( self.file_path, "dataset_%d_files" % self.id )
            #only use path directly under self.file_path if it exists
            if not os.path.exists( path ):
                path = os.path.join( os.path.join( self.file_path, *directory_hash_id( self.id ) ), "dataset_%d_files" % self.id )
        # Make path absolute
        return os.path.abspath( path )
    
    @property
    def datatype( self ):
        return datatypes_registry.get_datatype_by_extension( self.extension )

    def get_metadata( self ):
        if not self._metadata:
            self._metadata = dict()
        return MetadataCollection( self, self.datatype.metadata_spec )
    def set_metadata( self, bunch ):
        # Needs to accept a MetadataCollection, a bunch, or a dict
        self._metadata = dict( bunch.items() )
    metadata = property( get_metadata, set_metadata )

    """
    This provide backwards compatibility with using the old dbkey
    field in the database.  That field now maps to "old_dbkey" (see mapping.py).
    """
    def get_dbkey( self ):
        dbkey = self.metadata.dbkey
        if not isinstance(dbkey, list): dbkey = [dbkey]
        if dbkey in [["?"], [None], []]: dbkey = [self.old_dbkey]
        if dbkey in [[None], []]: return "?"
        return dbkey[0]
    def set_dbkey( self, value ):
        if "dbkey" in self.datatype.metadata_spec:
            if not isinstance(value, list): 
                self.metadata.dbkey = [value]
            else: 
                self.metadata.dbkey = value
        if isinstance(value, list): 
            self.old_dbkey = value[0]
        else:
            self.old_dbkey = value
    dbkey = property( get_dbkey, set_dbkey )

    def change_datatype( self, new_ext ):
        self.clear_associated_files()
        datatypes_registry.change_datatype( self, new_ext )
    def get_size( self ):
        """Returns the size of the data on disk"""
        if self.file_size:
            return self.file_size
        else:
            try:
                return os.path.getsize( self.file_name )
            except OSError:
                return 0
    def set_size( self ):
        """Returns the size of the data on disk"""
        try:
            self.file_size = os.path.getsize( self.file_name )
        except OSError:
            self.file_size = 0
    def has_data( self ):
        """Detects whether there is any data"""
        return self.get_size() > 0        
    def get_raw_data( self ):
        """Returns the full data. To stream it open the file_name and read/write as needed"""
        return self.datatype.get_raw_data( self )
    def write_from_stream( self, stream ):
        """Writes data from a stream"""
        self.datatype.write_from_stream(self, stream)
    def set_raw_data( self, data ):
        """Saves the data on the disc"""
        self.datatype.set_raw_data(self, data)
    def get_mime( self ):
        """Returns the mime type of the data"""
        return datatypes_registry.get_mimetype_by_extension( self.extension.lower() )
    def set_peek( self ):
        return self.datatype.set_peek( self )
    def init_meta( self, copy_from=None ):
        return self.datatype.init_meta( self, copy_from=copy_from )
    def set_meta( self, **kwd ):
        self.clear_associated_files( metadata_safe = True )
        return self.datatype.set_meta( self, **kwd )
    def set_readonly_meta( self, **kwd ):
        return self.datatype.set_readonly_meta( self, **kwd )
    def missing_meta( self ):
        return self.datatype.missing_meta( self )
    def as_display_type( self, type, **kwd ):
        return self.datatype.as_display_type( self, type, **kwd )
    def display_peek( self ):
        return self.datatype.display_peek( self )
    def display_name( self ):
        return self.datatype.display_name( self )
    def display_info( self ):
        return self.datatype.display_info( self )
    def get_associated_files_by_type( self, file_type ):
        valid = []
        for assoc in self.associated_files:
            if not assoc.deleted and assoc.type == file_type:
                valid.append( assoc )
        return valid
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        #metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.associated_files:
            if not metadata_safe or not assoc.metadata_safe:
                assoc.clear( purge = purge )
    def get_child_by_designation(self, designation):
        # if self.history:
        #     for data in self.history.datasets:
        #         if data.parent_id and data.parent_id == self.id:
        #             if designation == data.designation:
        #                 return data
        for child_association in self.children:
            if child_association.designation == designation:
                return child_association.child
        return None
    def get_converter_types(self):
        return self.datatype.get_converter_types( self, datatypes_registry)
    
    def copy(self, parent_id=None):
        des = Dataset(extension=self.ext)
        des.flush()
        des.name = self.name
        des.info = self.info
        des.blurb = self.blurb
        des.peek = self.peek
        des.extension = self.extension
        des.dbkey = str( self.dbkey )
        des.state = self.state
        des.metadata = self.metadata
        des.hid = self.hid
        des.deleted = self.deleted
        des.purged = self.purged
        # Make sure source is using filename table, so purge works properly
        if not self.dataset_file:
            self.set_file_name(self.file_name)
            self.flush()
            self.refresh()
            self.dataset_file.extra_files_path = self.extra_files_path
            self.flush()
        # Don't copy file contents, share original file
        des.file_name = self.file_name
        des.hid = self.hid
        des.designation = self.designation
        des.flush()
        return des

    def add_validation_error( self, validation_error ):
        self.validation_errors.append( validation_error )

    def extend_validation_errors( self, validation_errors ):
        self.validation_errors.extend(validation_errors)

    def mark_deleted( self, include_children=True ):
        self.deleted = True
        if include_children:
            for child_assoc in self.children:
                child_assoc.child.mark_deleted()
            

    # FIXME: sqlalchemy will replace this
    def _delete(self):
        """Remove the file that corresponds to this data"""
        try:
            os.remove(self.data.file_name)
        except OSError, e:
            log.critical('%s delete error %s' % (self.__class__.__name__, e))

class DatasetFileName( object ):
    def __init__( self, filename=None, readonly=False, extra_files_path=None ):
        self.filename = filename
        self.readonly = readonly
        self.extra_files_path = extra_files_path

class Old_Dataset( Dataset ):
    pass
            
class ValidationError( object ):
    def __init__( self, message=None, err_type=None, attributes=None ):
        self.message = message
        self.err_type = err_type
        self.attributes = attributes

class DatasetToValidationErrorAssociation( object ):
    def __init__( self, dataset, validation_error ):
        self.dataset = dataset
        self.validation_error = validation_error

class DatasetChildAssociation( object ):
    def __init__( self, designation=None ):
        self.designation = designation
        self.parent = None
        self.child = None

class DatasetAssociatedFile( object ):
    def __init__( self, id = None, dataset_id = None, file_type = None, parent_id = None, filename = None, deleted = False, purged = False, metadata_safe = True ):
        self.id = id
        self.dataset_id = dataset_id
        self.type = file_type
        self.parent_id = parent_id
        self.filename = filename
        self.deleted = deleted
        self.purged = purged
        self.metadata_safe = metadata_safe

    def get_file_name( self ):
        #return absolute path of the filename
        if self.filename:
            return os.path.abspath( self.filename )
        if self.dataset_id is not None:
            return self.dataset.file_name
        else:
            assert self.id is not None, "ID must be set before filename used (commit the object)"
            assert self.parent_id is not None, "Parent ID must be set before filename used"
            return os.path.abspath( "%s_accociated_%s" % ( self.parent.file_name, self.id ) )
    def set_file_name ( self, filename ):
        self.filename = filename
        if self.dataset:
            self.dataset.deleted = True
            self.dataset = None
            self.dataset_id = None
    file_name = property( get_file_name, set_file_name )

    def clear( self, purge = False ):
        self.deleted = True
        if self.dataset:
            self.dataset.deleted = True
            self.dataset.purged = purge
        if purge:
            self.purged = True
            try: os.unlink( self.file_name )
            except Exception, e: print "Failed to purge associated file (%s) from disk: %s" % ( self.file_name, e )

class Event( object ):
    def __init__( self, message=None, history=None, user=None, galaxy_session=None ):
        self.history = history
        self.galaxy_session = galaxy_session
        self.user = user
        self.tool_id = None
        self.message = message

class GalaxySession( object ):
    def __init__( self, id=None, user=None, remote_host=None, remote_addr=None, referer=None, current_history_id=None, session_key=None, is_valid=False, prev_session_id=None ):
        self.id = id
        self.user = user
        self.remote_host = remote_host
        self.remote_addr = remote_addr
        self.referer = referer
        self.current_history_id = current_history_id
        self.session_key = session_key
        self.is_valid = is_valid
        self.prev_session_id = prev_session_id
        self.histories = []

    def add_history( self, history, association=None ):
        if association is None:
            self.histories.append( GalaxySessionToHistoryAssociation( self, history ) )
        else:
            self.histories.append( association )
    
class GalaxySessionToHistoryAssociation( object ):
    def __init__( self, galaxy_session, history ):
        self.galaxy_session = galaxy_session
        self.history = history
        
class StoredWorkflow( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.name = None
        self.latest_workflow_id = None
        self.workflows = []

class Workflow( object ):
    def __init__( self ):
        self.user = None
        self.name = None
        self.has_cycles = None
        self.has_errors = None
        self.steps = []
        
class WorkflowStep( object ):
    def __init__( self ):
        self.id = None
        self.type = None
        self.tool_id = None
        self.tool_inputs = None
        self.tool_errors = None
        self.position = None
        self.input_connections = None
        self.config = None
        
class WorkflowStepConnection( object ):
    def __init__( self ):
        self.output_step_id = None
        self.output_name = None
        self.input_step_id = None
        self.input_name = None

## ---- Utility methods -------------------------------------------------------

def directory_hash_id( id ):
    s = str( id )
    l = len( s )
    # Shortcut -- ids 0-999 go under ../000/
    if l < 4:
        return [ "000" ]
    # Pad with zeros until a multiple of three
    padded = ( ( 3 - len( s ) % 3 ) * "0" ) + s
    # Drop the last three digits -- 1000 files per directory
    padded = padded[:-3]
    # Break into chunks of three
    return [ padded[i*3:(i+1)*3] for i in range( len( padded ) // 3 ) ]
