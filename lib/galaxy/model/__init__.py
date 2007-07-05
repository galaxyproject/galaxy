"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""

import os.path
import sha
import galaxy.datatypes
from cookbook.patterns import Bunch
from galaxy import util
import tempfile
import galaxy.datatypes.registry
from galaxy.datatypes.metadata import MetadataCollection

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
                    ERROR = 'error' )
    def __init__( self ):
        self.session_id = None
        self.tool_id = None
        self.command_line = None
        self.param_filename = None
        self.parameters = []
        self.input_datasets = []
        self.output_datasets = []
        self.state = Job.states.NEW
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

    def add_galaxy_session( self, galaxy_session ):
        self.galaxy_sessions.append( GalaxySessionToHistoryAssociation( galaxy_session, self ) )
    
    def add_dataset( self, dataset, parent_id=None, genome_build=None ):
        if parent_id:
            for data in self.datasets:
                if data.id == parent_id:
                    dataset.hid = data.hid
                    break
            else:
                dataset.hid = self._next_hid()
        else:
            dataset.hid = self._next_hid()
        self.genome_build = genome_build
        self.datasets.append( dataset )

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
                    FAKE = 'fake' )
    file_path = "/tmp/"
    engine = None
    def __init__( self, id=None, hid=None, name=None, info=None, blurb=None, peek=None, extension=None, 
                  dbkey=None, state=None, metadata=None, history=None, parent_id=None, designation=None,
                  validation_errors=None ):
        self.name = name or "Unnamed dataset"
        self.id = id
        self.hid = hid
        self.info = info
        self.blurb = blurb
        self.peek = peek
        self.extension = extension
        self.dbkey = dbkey
        self.state = state
        self._metadata = metadata or Bunch()
        self.parent_id = parent_id
        self.designation = designation
        self.deleted = False
        self.purged = False
        # Relationships
        self.history = history
        self.validation_errors = validation_errors

    # Deprecated: the metadatacollection now updates the object
    # reference whenever any metadata is changed
    def mark_metadata_changed( self ):
        """
        Register changes to metadata with the history
        
        FIXME: This is just temporary, I'd like to implement some kind of 
               object proxy mapper property for SQLAlchemy that handles 
               this magically.

               Fixed.  INS, 7/5/2007  Waiting to remove...
        """
        self._metadata = Bunch( **self._metadata.__dict__ )
        
    @property
    def ext( self ):
        return self.extension
    @property
    def file_name( self ):
        assert self.id is not None, "ID must be set before filename used (commit the object)"
        return os.path.join( self.file_path, "dataset_%d.dat" % self.id )
    @property
    def datatype( self ):
        return datatypes_registry.get_datatype_by_extension( self.extension )

    def get_metadata( self ):
        if not self._metadata: self._metadata = Bunch()
        return MetadataCollection( self, self.datatype.get_metadata_spec() )
    def set_metadata( self, bunch ):
        # Needs to accept a MetadataCollection, a bunch, or a dict
        self._metadata = Bunch( **dict( bunch.items() ) )
    metadata = property( get_metadata, set_metadata )
    
    def change_datatype( self, new_ext ):
        datatypes_registry.change_datatype( self, new_ext )
    def get_size( self ):
        """
        Returns the size of the data on disk
        """
        try:
            return os.path.getsize( self.file_name )
        except OSError, e:
            return 0
    def has_data( self ):
        """Detects whether there is any data"""
        return self.get_size() > 0        
    def get_raw_data( self ):
        """Returns the full data. To stream it open the file_name and read/write as needed"""
        try:
            return file(self.file_name, 'rb').read(-1)
        except OSError, e:
            log.exception('%s reading a file that does not exist %s' % (self.__class__.__name__))
            return ''
    def write_from_stream(self, stream):
        "Writes data from a stream"
        # write it twice for now 
        fd, temp_name = tempfile.mkstemp()
        while 1:
            chunk = stream.read(1048576)
            if not chunk:
                break
            os.write(fd, chunk)
        os.close(fd)
        # rewrite the file with unix newlines
        fp = open(self.file_name, 'wt')
        for line in file(temp_name, "U"):
            line = line.strip() + '\n'
            fp.write(line)
        fp.close()
    def set_raw_data(self, data):
        """Saves the data on the disc"""
        fd, temp_name = tempfile.mkstemp()
        os.write(fd, data)
        os.close(fd)
        # rewrite the file with unix newlines
        fp = open(self.file_name, 'wt')
        for line in file(temp_name, "U"):
            line = line.strip() + '\n'
            fp.write(line)
        fp.close()
        os.remove( temp_name )
    def get_mime(self):
        """Returns the mime type of the data"""
        return datatypes_registry.get_mimetype_by_extension( self.extension.lower() )
    def set_peek( self ):
        return self.datatype.set_peek( self )
    def init_meta( self ):
        return self.datatype.init_meta( self )
    def set_meta( self, first_line_is_header=False ):
        return self.datatype.set_meta( self, first_line_is_header )
    def missing_meta( self ):
        return self.datatype.missing_meta( self )
    def get_estimated_display_viewport( self ):
        return self.datatype.get_estimated_display_viewport( self )
    def as_ucsc_display_file( self ):
        return self.datatype.as_ucsc_display_file( self )
    def as_gbrowse_display_file( self ):
        return self.datatype.as_gbrowse_display_file( self )
    def display_peek( self ):
        return self.datatype.display_peek( self )
    def display_name( self ):
        return self.datatype.display_name( self )
    def display_info( self ):
        return self.datatype.display_info( self )
    def get_ucsc_sites( self ):
        return self.datatype.get_ucsc_sites( self )
    def get_gbrowse_sites( self ):
        return self.datatype.get_gbrowse_sites( self )
    def get_child_by_designation(self, designation):
        # if self.history:
        #     for data in self.history.datasets:
        #         if data.parent_id and data.parent_id == self.id:
        #             if designation == data.designation:
        #                 return data
        for child_assocation in self.children:
            if child_association.designation == designation:
                return child
        return None
    def purge( self ):
        """Removes the file contents from disk """
        self.deleted = True
        self.purged = True
        try: os.unlink(self.file_name)
        except: pass

    def add_validation_error( self, validation_error ):
        self.validation_errors.append( validation_error )

    def extend_validation_errors( self, validation_errors ):
        self.validation_errors.extend(validation_errors)

    # FIXME: sqlalchemy will replace this
    def _delete(self):
        """Remove the file that corresponds to this data"""
        try:
            os.remove(self.data.file_name)
        except OSError, e:
            log.critical('%s delete error %s' % (self.__class__.__name__, e))
            
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
            
class Event( object ):
    def __init__( self, message=None, history=None, user=None, galaxy_session=None ):
        self.history = history
        self.galaxy_session = galaxy_session
        self.user = user
        self.tool_id = None
        self.message = message

class GalaxySession( object ):
    def __init__( self, id=None, user=None, remote_host=None, remote_addr=None, referer=None ):
        self.id = id
        self.user = user
        self.remote_host = remote_host
        self.remote_addr = remote_addr
        self.referer = referer
        self.histories = []

    def add_history( self, history ):
        self.histories.append( GalaxySessionToHistoryAssociation( self, history ) )
    
class GalaxySessionToHistoryAssociation( object ):
    def __init__( self, galaxy_session, history ):
        self.galaxy_session = galaxy_session
        self.history = history
