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
    >>> DataTest.metadata_spec.test.attributes
    >>> DataTest.metadata_spec.test.param
    <class 'galaxy.datatypes.metadata.MetadataParameter'>
    
    """
    __metaclass__ = DataMeta
    
    """Provide the set of display formats supported by this datatype """
    supported_display_apps = []

    def set_peek( self, dataset ):
        dataset.peek  = ''
        dataset.blurb = 'data'
    def init_meta( self, dataset, copy_from=None ):
        # Metadata should be left mostly uninitialized.  Dataset will
        # handle returning default values when metadata is not set.
        # copy_from allows metadata to be passed in that will be
        # copied. (although this seems ambiguous, see
        # Dataset.set_metadata.  It always copies the rhs in order to
        # flag the object as modified for SQLAlchemy.
        if copy_from:
            dataset.metadata = copy_from.metadata
    def missing_meta( self, dataset):
        return False
    def get_estimated_display_viewport( self, dataset ):
        raise Exception( "'get_estimated_display_viewport' must be overridden in subclass." )
    def as_ucsc_display_file( self, dataset ):
        raise Exception( "'as_ucsc_display_file' not supported for this datatype" )
    def as_gbrowse_display_file( self, dataset ):
        raise Exception( "'as_gbrowse_display_file' not supported for this datatype" )
    def display_peek(self, dataset):
        try:
            return escape(dataset.peek)
        except:
            return "peek unavailable"
    def display_name(self, dataset):
        try:
            return escape(dataset.name)
        except:
            return "name unavailable"
    def display_info(self, dataset):
        try:
            return escape(dataset.info)
        except:
            return "info unavailable"
    def get_ucsc_sites(self, dataset):
        return util.get_ucsc_by_build(dataset.dbkey)
    def get_gbrowse_sites(self, dataset):
        return util.get_gbrowse_sites_by_build(dataset.dbkey)
    def validate(self, dataset):
        """Unimplemented validate, return no exceptions"""
        return list()
    def repair_methods(self, dataset):
        """Unimplemented method, returns dict with method/option for repairing errors"""
        return None

class Text( Data ):

    """Provide the set of display formats supported by this datatype """
    supported_display_apps = []

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

    def delete(self):
        """Remove the file that corresponds to this data"""
        obj.DBObj.delete(self)
        try:
            os.remove(self.file_name)
        except OSError, e:
            log.critical('%s delete error %s' % (self.__class__.__name__, e))

# Removed for now ... this should be handled specifically by the registry
##     def get_mime(self):
##         """Returns the mime type of the data"""
##         return galaxy.datatypes.registry.Registry().get_mimetype_by_extension( self.extension.lower() )
   
    def set_peek(self, dataset):
        dataset.peek  = get_file_peek( dataset.file_name )
        dataset.blurb = util.commaify( str( get_line_count( dataset.file_name ) ) ) + " lines"

class Binary( Data ):
    """Binary data"""

    """Provide the set of display formats supported by this datatype """
    supported_display_apps = []

    def set_peek( self, dataset ):
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
