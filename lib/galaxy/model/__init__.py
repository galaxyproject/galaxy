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
        self.tool_id = None
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
        # Relationships
        self.user = user
        self.datasets = []
        
    def __next_hid( self ):
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
    
    def add_dataset( self, dataset, parent_id=None ):
        if parent_id:
            for data in self.datasets:
                if data.id == parent_id:
                    dataset.hid = data.hid
                    break
            else:
                dataset.hid = self.__next_hid()
        else:
            dataset.hid = self.__next_hid()
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
                  dbkey=None, state=None, metadata=None, history=None, parent_id=None, designation=None ):
        self.name = name or "Unnamed dataset"
        self.id = id
        self.hid = hid
        self.info = info
        self.blurb = blurb
        self.peek = peek
        self.extension = extension
        self.dbkey = dbkey
        self.state = state
        self.metadata = metadata or Bunch()
        self.parent_id = parent_id
        self.designation = designation
        # Relationships
        self.history = history
    def mark_metadata_changed( self ):
        """
        Register changes to metadata with the history
        
        FIXME: This is just temporary, I'd like to implement some kind of 
               object proxy mapper property for SQLAlchemy that handles 
               this magically.
        """
        self.metadata = Bunch( **self.metadata.__dict__ )
    @property
    def ext( self ):
        return self.extension
    @property
    def file_name( self ):
        assert self.id is not None, "ID must be set before filename used (commit the object)"
        return os.path.join( self.file_path, "dataset_%d.dat" % self.id )
    @property
    def datatype( self ):
        return galaxy.datatypes.get_datatype_by_extension( self.extension )
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
        try:
            ext = self.extension.lower()
            if ext in util.text_types:
                return 'text/plain'
            return util.mime_types[ext]
        except KeyError:
            return 'application/octet-stream'
    def set_peek( self ):
        return self.datatype.set_peek( self )
    def init_meta( self ):
        return self.datatype.init_meta( self )
    def missing_meta( self ):
        return self.datatype.missing_meta( self )
    def bed_viewport( self ):
        return self.datatype.bed_viewport( self )
    def as_bedfile( self ):
        return self.datatype.as_bedfile( self )
    def display_peek( self ):
        return self.datatype.display_peek( self )
    def display_name( self ):
        return self.datatype.display_name( self )
    def display_info( self ):
        return self.datatype.display_info( self )
    def get_ucsc_sites( self ):
        return self.datatype.get_ucsc_sites( self )
    def get_child_by_designation(self, designation):
        if self.history:
            for data in self.history.datasets:
                if data.parent_id and data.parent_id == self.id:
                    if designation == data.designation:
                        return data
        return None
    # FIXME: sqlalchemy will replace this
    def _delete(self):
        """Remove the file that corresponds to this data"""
        try:
            os.remove(self.data.file_name)
        except OSError, e:
            log.critical('%s delete error %s' % (self.__class__.__name__, e))
            
class Event( object ):
    def __init__( self, message=None, history=None, user=None ):
        self.message = message
        self.history = history
        self.user = user
