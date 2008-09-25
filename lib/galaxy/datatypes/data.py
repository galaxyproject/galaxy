import logging, os, sys, time, sets, tempfile
from galaxy import util
from cgi import escape
from galaxy.datatypes.metadata import *
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata

log = logging.getLogger(__name__)

# Valid first column and strand column values vor bed, other formats
col1_startswith = ['chr', 'chl', 'groupun', 'reftig_', 'scaffold', 'super_', 'vcho']
valid_strand = ['+', '-', '.']
gzip_magic = '\037\213'

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
    
    """Add metadata elements"""
    MetadataElement( name="dbkey", desc="Database/Build", default="?", param=metadata.SelectParameter, multiple=False, values=util.dbnames, no_value="?" )
    
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
    def set_meta( self, dataset, overwrite = True, **kwd ):
        """Unimplemented method, allows guessing of metadata from contents of file"""
        return True
    def set_readonly_meta( self, dataset ):
        """Unimplemented method, resets the readonly metadata values"""
        return True
    def missing_meta( self, dataset ):
        """Checks for empty metadata values, Returns True if non-optional metadata is missing"""
        for key, value in dataset.metadata.items():
            if dataset.metadata.spec[key].get("optional"): continue #we skip check for optional values here
            if not value:
                return True
        return False
    def set_peek( self, dataset ):
        """Set the peek and blurb text"""
        dataset.peek  = ''
        dataset.blurb = 'data'
    def display_peek(self, dataset):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        try:
            if not dataset.peek:
                dataset.set_peek()
            data = dataset.peek
            lines =  data.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                out.append( '<tr><td>%s</td></tr>' % escape( line ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % str( exc )
        return out
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

    def get_converter_types(self, original_dataset, datatypes_registry):
        """Returns available converters by type for this dataset"""
        return datatypes_registry.get_converters_by_datatype(original_dataset.ext)
    
    def convert_dataset(self, trans, original_dataset, target_type, return_output = False, visible = True ):
        """This function adds a job to the queue to convert a dataset to another type. Returns a message about success/failure."""
        converter = trans.app.datatypes_registry.get_converter_by_target_type( original_dataset.ext, target_type )
        if converter is None:
            raise "A converter does not exist for %s to %s." % ( original_dataset.ext, target_type )
        
        #Generate parameter dictionary
        params = {}
        #determine input parameter name and add to params
        input_name = 'input1'
        for key, value in converter.inputs.items():
            if value.type == 'data':
                input_name = key
                break
        params[input_name] = original_dataset
        
        #Run converter, job is dispatched through Queue
        converted_dataset = converter.execute( trans, incoming = params, set_output_hid = visible )
        
        if len(params) > 0:
            trans.log_event( "Converter params: %s" % (str(params)), tool_id=converter.id )
        
        if not visible:
            for name, value in converted_dataset.iteritems():
                value.visible = False
        
        if return_output:
            return converted_dataset
        return "The file conversion of %s on data %s has been added to the Queue." % (converter.name, original_dataset.hid)

    def before_edit( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

    def after_edit( self, dataset ):
        """This function is called on the dataset after metadata is edited."""
        dataset.clear_associated_files( metadata_safe = True )

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
   
    def set_peek( self, dataset, line_count=None ):
        dataset.peek  = get_file_peek( dataset.file_name )
        if line_count is None:
            dataset.blurb = "%s lines" % util.commaify( str( get_line_count( dataset.file_name ) ) )
        else:
            dataset.blurb = "%s lines" % util.commaify( str( line_count ) )

class Binary( Data ):
    """Binary data"""

    def set_peek( self, dataset ):
        """Set the peek and blurb text"""
        dataset.peek  = 'binary data'
        dataset.blurb = 'data'

def get_test_fname( fname ):
    """Returns test data filename"""
    path, name = os.path.split(__file__)
    full_path = os.path.join( path, 'test', fname )
    return full_path

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
    try:
        size = float( size )
    except:
        return '??? bytes'
    for ind, word in enumerate(words):
        step  = 1024 ** (ind + 1)
        if step > size:
            size = size / float(1024 ** ind)
            out  = "%.1f %s" % (size, word)
            return out
    return '??? bytes'

def get_file_peek( file_name, WIDTH=256, LINE_COUNT=5 ):
    """
    Returns the first LINE_COUNT lines wrapped to WIDTH
    
    >>> fname = get_test_fname('4.bed')
    >>> get_file_peek(fname)
    'chr22    30128507    31828507    uc003bnx.1_cds_2_0_chr22_29227_f    0    +\n'
    """
    lines = []
    count = 0
    file_type = ''
    data_checked = False
    for line in file( file_name ):
        line = line[ :WIDTH ]
        if not data_checked and line:
            data_checked = True
            if line[0:2] == gzip_magic:
                file_type = 'gzipped'
                break
            else:
                for char in line:
                    if ord( char ) > 128:
                        file_type = 'binary'
                        break
        lines.append( line )
        if count == LINE_COUNT: 
            break
        count += 1
    if file_type: 
        text = "%s file" %file_type 
    else: 
        text  = '\n'.join( lines )
    return text

def get_line_count(file_name):
    """Returns the number of lines in a file that are neither null nor comments"""
    count = 0
    for line in file(file_name):
        line = line.strip()
        if line and line[0] != '#':
            count += 1
    return count

class Newick( Text ):
    pass
