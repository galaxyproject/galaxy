import logging, os, sys, time, sets, tempfile
from galaxy import util
from cgi import escape
from galaxy.datatypes.metadata import *
log = logging.getLogger(__name__)

# Constants for data states
DATA_NEW, DATA_OK, DATA_FAKE = 'new', 'ok', 'fake'

class DataMeta( type ):
    """
    Metaclass for Data class.  Sets up metadata spec.
    """
    def __init__( cls, name, bases, dict_ ):
        cls.metadata_spec = MetadataSpecCollection()
        for base in bases:
            if hasattr(base, "metadata_spec"):
                cls.metadata_spec.update(base.metadata_spec)
        Statement.process( cls )

class Data( object ):
    """
    Base class for all datatypes.  Implements basic interfaces as well
    as class methods for metadata.

    >>> class DataTest( Data ):
    ...     MetadataElement( name="test" )
    ...
    >>> DataTest.metadata_spec.test.name
    'test'
    >>> DataTest.metadata_spec.test.desc
    'test'
    >>> DataTest.metadata_spec.test.param
    <class 'galaxy.datatypes.metadata.MetadataParameter'>
    
    """
    __metaclass__ = DataMeta
    
    """Stores the set of display applications, and viewing methods, supported by this datatype """
    supported_display_apps = {}
    
    def __init__(self, **kwd):
        """Initialize the datatype"""
        object.__init__(self, **kwd)
        self.supported_display_apps = self.supported_display_apps.copy()
    
    def write_from_stream(self, dataset, stream):
        """Writes data from a stream"""
        fd = open(dataset.file_name, 'wb')
        while 1:
            chunk = stream.read(1048576)
            if not chunk:
                break
            os.write(fd, chunk)
        os.close(fd)

    def set_raw_data(self, dataset, data):
        """Saves the data on the disc"""
        fd = open(dataset.file_name, 'wb')
        os.write(fd, data)
        os.close(fd)
    
    def get_raw_data( self, dataset ):
        """Returns the full data. To stream it open the file_name and read/write as needed"""
        try:
            return file(datset.file_name, 'rb').read(-1)
        except OSError, e:
            log.exception('%s reading a file that does not exist %s' % (self.__class__.__name__, dataset.file_name))
            return ''

    def init_meta( self, dataset, copy_from=None ):
        # Metadata should be left mostly uninitialized.  Dataset will
        # handle returning default values when metadata is not set.
        # copy_from allows metadata to be passed in that will be
        # copied. (although this seems ambiguous, see
        # Dataset.set_metadata.  It always copies the rhs in order to
        # flag the object as modified for SQLAlchemy.
        if copy_from:
            dataset.metadata = copy_from.metadata
    def set_meta( self, dataset ):
        """Unimplemented method, allows guessing of metadata from contents of file"""
        return True
    def missing_meta( self, dataset):
        """Unimplemented method, Returns True if metadata is missing"""
        return False
    def set_peek( self, dataset ):
        """Set the peek and blurb text"""
        dataset.peek  = ''
        dataset.blurb = 'data'
    def display_peek(self, dataset):
        """Returns formated html of peek"""
        try:
            return escape(dataset.peek)
        except:
            return "peek unavailable"
    def display_name(self, dataset):
        """Returns formated html of dataset name"""
        try:
            return escape(dataset.name)
        except:
            return "name unavailable"
    def display_info(self, dataset):
        """Returns formated html of dataset info"""
        try:
            return escape(dataset.info)
        except:
            return "info unavailable"
    def validate(self, dataset):
        """Unimplemented validate, return no exceptions"""
        return list()
    def repair_methods(self, dataset):
        """Unimplemented method, returns dict with method/option for repairing errors"""
        return None
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'
    def add_display_app (self, app_id, label, file_function, links_function ):
        """
        Adds a display app to the datatype.
        app_id is a unique id
        label is the primary display label, ie display at 'UCSC'
        file_function is a string containing the name of the function that returns a properly formated display
        links_function is a string containing the name of the function that returns a list of (link_name,link)
        """
        self.supported_display_apps = self.supported_display_apps.copy()
        self.supported_display_apps[app_id] = {'label':label,'file_function':file_function,'links_function':links_function}
    def remove_display_app (self, app_id):
        """Removes a display app from the datatype"""
        self.supported_display_apps = self.supported_display_apps.copy()
        try:
            del self.supported_display_apps[app_id]
        except:
            log.exception('Tried to remove display app %s from datatype %s, but this display app is not declared.' % ( type, self.__class__.__name__ ) )
    def get_display_types(self):
        """Returns display types available"""
        return self.supported_display_apps.keys()
    def get_display_label(self, type):
        """Returns primary label for display app"""
        try:
            return self.supported_display_apps[type]['label']
        except:
            return 'unknown'
    def as_display_type(self, dataset, type, **kwd):
        """Returns modified file contents for a particular display type """
        try:
            if type in self.get_display_types():
                return getattr (self, self.supported_display_apps[type]['file_function']) (dataset, **kwd)
        except:
            log.exception('Function %s is referred to in datatype %s for displaying as type %s, but is not accessible' % (self.supported_display_apps[type]['file_function'], self.__class__.__name__, type) )
        return "This display type (%s) is not implemented for this datatype (%s)." % ( type, dataset.ext)
        
    def get_display_links(self, dataset, type, app, base_url, **kwd):
        """Returns a list of tuples of (name, link) for a particular display type """
        try:
            if type in self.get_display_types():
                return getattr (self, self.supported_display_apps[type]['links_function']) (dataset, type, app, base_url, **kwd)
        except:
            log.exception('Function %s is referred to in datatype %s for generating links for type %s, but is not accessible' % (self.supported_display_apps[type]['links_function'], self.__class__.__name__, type) )
        return []

    def before_edit( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

    def after_edit( self, dataset ):
        """This function is called on the dataset after metadata is edited."""
        pass

class Text( Data ):

    def write_from_stream(self, dataset, stream):
        """Writes data from a stream"""
        # write it twice for now 
        fd, temp_name = tempfile.mkstemp()
        while 1:
            chunk = stream.read(1048576)
            if not chunk:
                break
            os.write(fd, chunk)
        os.close(fd)

        # rewrite the file with unix newlines
        fp = open(dataset.file_name, 'wt')
        for line in file(temp_name, "U"):
            line = line.strip() + '\n'
            fp.write(line)
        fp.close()

    def set_raw_data(self, dataset, data):
        """Saves the data on the disc"""
        fd, temp_name = tempfile.mkstemp()
        os.write(fd, data)
        os.close(fd)

        # rewrite the file with unix newlines
        fp = open(dataset.file_name, 'wt')
        for line in file(temp_name, "U"):
            line = line.strip() + '\n'
            fp.write(line)
        fp.close()

        os.remove( temp_name )
    
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/plain'
   
    def set_peek(self, dataset):
        dataset.peek  = get_file_peek( dataset.file_name )
        dataset.blurb = util.commaify( str( get_line_count( dataset.file_name ) ) ) + " lines"

class Binary( Data ):
    """Binary data"""

    def set_peek( self, dataset ):
        """Set the peek and blurb text"""
        dataset.peek  = 'binary data'
        dataset.blurb = 'data'

def nice_size(size):
    """
    Returns a readably formatted string with the size

    >>> nice_size(100)
    '100.0 bytes'
    >>> nice_size(10000)
    '9.8 Kb'
    >>> nice_size(1000000)
    '976.6 Kb'
    >>> nice_size(100000000)
    '95.4 Mb'
    """
    words = [ 'bytes', 'Kb', 'Mb', 'Gb' ]
    for ind, word in enumerate(words):
        step  = 1024 ** (ind + 1)
        if step > size:
            size = size / float(1024 ** ind)
            out  = "%.1f %s" % (size, word)
            return out
    return '??? bytes'

def get_file_peek(file_name, WIDTH=256, LINE_COUNT=5 ):
    """Returns the first LINE_COUNT lines wrapped to WIDTH"""
    
    lines = []
    count = 0
    for line in file(file_name):
        line = line.strip()[:WIDTH]
        lines.append(line)
        if count==LINE_COUNT:
            break
        count += 1
    text  = '\n'.join(lines)
    return text

def get_line_count(file_name):
    """Returns the number of lines in a file that are neither null nor comments"""
    count = 0
    for line in file(file_name):
        line = line.strip()
        if line and line[0] != '#':
            count += 1
    return count
