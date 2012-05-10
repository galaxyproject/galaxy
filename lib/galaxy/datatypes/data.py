import logging, os, sys, time, tempfile
from galaxy import util
from galaxy.util.odict import odict
from galaxy.util.bunch import Bunch
from galaxy.util import inflector
from galaxy.util.sanitize_html import sanitize_html
from cgi import escape
import mimetypes
import metadata
import zipfile
from metadata import MetadataElement #import directly to maintain ease of use in Datatype class definitions


if sys.version_info[:2] < ( 2, 6 ):
    zipfile.BadZipFile = zipfile.error
if sys.version_info[:2] < ( 2, 5 ):
    zipfile.LargeZipFile = zipfile.error

tmpd = tempfile.mkdtemp()
comptypes=[]
ziptype = '32'
tmpf = os.path.join( tmpd, 'compression_test.zip' )
try:
    archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
    archive.close()
    comptypes.append( 'zip' )
    ziptype = '64'
except RuntimeError:
    log.exception( "Compression error when testing zip compression. This option will be disabled for library downloads." )
except (TypeError, zipfile.LargeZipFile):    # ZIP64 is only in Python2.5+.  Remove TypeError when 2.4 support is dropped
    log.warning( 'Max zip file size is 2GB, ZIP64 not supported' )
    comptypes.append( 'zip' )
try:
    os.unlink( tmpf )
except OSError:
    pass
os.rmdir( tmpd )

log = logging.getLogger(__name__)

# Valid first column and strand column values vor bed, other formats
col1_startswith = ['chr', 'chl', 'groupun', 'reftig_', 'scaffold', 'super_', 'vcho']
valid_strand = ['+', '-', '.']

class DataMeta( type ):
    """
    Metaclass for Data class.  Sets up metadata spec.
    """
    def __init__( cls, name, bases, dict_ ):
        cls.metadata_spec = metadata.MetadataSpecCollection()
        for base in bases: #loop through bases (class/types) of cls
            if hasattr( base, "metadata_spec" ): #base of class Data (object) has no metadata
                cls.metadata_spec.update( base.metadata_spec ) #add contents of metadata spec of base class to cls
        metadata.Statement.process( cls )

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
    >>> type( DataTest.metadata_spec.test.param )
    <class 'galaxy.datatypes.metadata.MetadataParameter'>

    """
    __metaclass__ = DataMeta
    # Add metadata elements
    MetadataElement( name="dbkey", desc="Database/Build", default="?", param=metadata.DBKeyParameter, multiple=False, no_value="?" )
    # Stores the set of display applications, and viewing methods, supported by this datatype
    supported_display_apps = {}
    # If False, the peek is regenerated whenever a dataset of this type is copied
    copy_safe_peek = True
    # The dataset contains binary data --> do not space_to_tab or convert newlines, etc.
    # Allow binary file uploads of this type when True.
    is_binary = True
    # Allow user to change between this datatype and others. If False, this datatype
    # cannot be changed from or into.
    allow_datatype_change = True
    #Composite datatypes
    composite_type = None
    composite_files = odict()
    primary_file_name = 'index'
    #A per datatype setting (inherited): max file size (in bytes) for setting optional metadata
    _max_optional_metadata_filesize = None

    def __init__(self, **kwd):
        """Initialize the datatype"""
        object.__init__(self, **kwd)
        self.supported_display_apps = self.supported_display_apps.copy()
        self.composite_files = self.composite_files.copy()
        self.display_applications = odict()
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
            return file(dataset.file_name, 'rb').read(-1)
        except OSError, e:
            log.exception('%s reading a file that does not exist %s' % (self.__class__.__name__, dataset.file_name))
            return ''
    def dataset_content_needs_grooming( self, file_name ):
        """This function is called on an output dataset file after the content is initially generated."""
        return False
    def groom_dataset_content( self, file_name ):
        """This function is called on an output dataset file if dataset_content_needs_grooming returns True."""
        pass
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
    def missing_meta( self, dataset, check = [], skip = [] ):
        """
        Checks for empty metadata values, Returns True if non-optional metadata is missing
        Specifying a list of 'check' values will only check those names provided; when used, optionality is ignored
        Specifying a list of 'skip' items will return True even when a named metadata value is missing
        """
        if check:
            to_check = [ ( to_check, dataset.metadata.get( to_check ) ) for to_check in check ]
        else:
            to_check = dataset.metadata.items()
        for key, value in to_check:
            if key in skip or ( not check and dataset.metadata.spec[key].get( "optional" ) ):
                continue #we skip check for optional and nonrequested values here
            if not value:
                return True
        return False
    def set_max_optional_metadata_filesize( self, max_value ):
        try:
            max_value = int( max_value )
        except:
            return
        self.__class__._max_optional_metadata_filesize = max_value
    def get_max_optional_metadata_filesize( self ):
        rval = self.__class__._max_optional_metadata_filesize
        if rval is None:
            return -1
        return rval
    max_optional_metadata_filesize = property( get_max_optional_metadata_filesize, set_max_optional_metadata_filesize )
    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = ''
            dataset.blurb = 'data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset ):
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
                if type( line ) is unicode:
                    out.append( '<tr><td>%s</td></tr>' % escape( line ) )
                else:
                    out.append( '<tr><td>%s</td></tr>' % escape( unicode( line, 'utf-8' ) ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % str( exc )
        return out

    def _archive_composite_dataset( self, trans, data=None, **kwd ):
        # save a composite object into a compressed archive for downloading
        params = util.Params( kwd )
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        outfname = data.name[0:150]
        outfname = ''.join(c in valid_chars and c or '_' for c in outfname)
        if (params.do_action == None):
            params.do_action = 'zip' # default
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if not data:
            msg = "You must select at least one dataset"
            messagetype = 'error'
        else:
            error = False
            try:
                if (params.do_action == 'zip'):
                    # Can't use mkstemp - the file must not exist first
                    tmpd = tempfile.mkdtemp()
                    tmpf = os.path.join( tmpd, 'library_download.' + params.do_action )
                    if ziptype == '64':
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
                    else:
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED )
                    archive.add = lambda x, y: archive.write( x, y.encode('CP437') )
                elif params.do_action == 'tgz':
                    archive = util.streamball.StreamBall( 'w|gz' )
                elif params.do_action == 'tbz':
                    archive = util.streamball.StreamBall( 'w|bz2' )
            except (OSError, zipfile.BadZipFile):
                error = True
                log.exception( "Unable to create archive for download" )
                msg = "Unable to create archive for %s for download, please report this error" % outfname
                messagetype = 'error'
            if not error:
                current_user_roles = trans.get_current_user_roles()
                ext = data.extension
                path = data.file_name
                fname = os.path.split(path)[-1]
                efp = data.extra_files_path
                htmlname = os.path.splitext(outfname)[0]
                if not htmlname.endswith(ext):
                    htmlname = '%s_%s' % (htmlname,ext)
                archname = '%s.html' % htmlname # fake the real nature of the html file
                try:
                    archive.add(data.file_name,archname)
                except IOError:
                    error = True
                    log.exception( "Unable to add composite parent %s to temporary library download archive" % data.file_name)
                    msg = "Unable to create archive for download, please report this error"
                    messagetype = 'error'
                for root, dirs, files in os.walk(efp):
                    for fname in files:
                        fpath = os.path.join(root,fname)
                        rpath = os.path.relpath(fpath,efp)
                        try:
                            archive.add( fpath,rpath )
                        except IOError:
                            error = True
                            log.exception( "Unable to add %s to temporary library download archive" % rpath)
                            msg = "Unable to create archive for download, please report this error"
                            messagetype = 'error'
                            continue
                if not error:
                    if params.do_action == 'zip':
                        archive.close()
                        tmpfh = open( tmpf )
                        # CANNOT clean up - unlink/rmdir was always failing because file handle retained to return - must rely on a cron job to clean up tmp
                        trans.response.set_content_type( "application/x-zip-compressed" )
                        trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.zip"' % outfname 
                        return tmpfh
                    else:
                        trans.response.set_content_type( "application/x-tar" )
                        outext = 'tgz'
                        if params.do_action == 'tbz':
                            outext = 'tbz'
                        trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % (outfname,outext) 
                        archive.wsgi_status = trans.response.wsgi_status()
                        archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                        return archive.stream
        return trans.show_error_message( msg )

    def _serve_raw(self, trans, dataset, to_ext):
        trans.response.headers['Content-Length'] = int( os.stat( dataset.file_name ).st_size )
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = ''.join(c in valid_chars and c or '_' for c in dataset.name)[0:150]
        trans.response.set_content_type( "application/octet-stream" ) #force octet-stream so Safari doesn't append mime extensions to filename
        trans.response.headers["Content-Disposition"] = 'attachment; filename="Galaxy%s-[%s].%s"' % (dataset.hid, fname, to_ext)
        return open( dataset.file_name )

    def display_data(self, trans, data, preview=False, filename=None, to_ext=None, size=None, offset=None, **kwd):
        """ Old display method, for transition """
        #Relocate all composite datatype display to a common location.
        composite_extensions = trans.app.datatypes_registry.get_composite_extensions( )
        composite_extensions.append('html') # for archiving composite datatypes
        if isinstance( data, basestring ):
            return data
        if filename and filename != "index":
            # For files in extra_files_path
            file_path = trans.app.object_store.get_filename(data.dataset, extra_dir='dataset_%s_files' % data.dataset.id, alt_name=filename)
            if os.path.exists( file_path ):
                if os.path.isdir( file_path ):
                    return trans.show_error_message( "Directory listing is not allowed." ) #TODO: Reconsider allowing listing of directories?
                mime, encoding = mimetypes.guess_type( file_path )
                if not mime:
                    try:
                        mime = trans.app.datatypes_registry.get_mimetype_by_extension( ".".split( file_path )[-1] )
                    except:
                        mime = "text/plain"
                trans.response.set_content_type( mime )
                return open( file_path )
            else:
                return trans.show_error_message( "Could not find '%s' on the extra files path %s." % ( filename, file_path ) )
        trans.response.set_content_type(data.get_mime())
        trans.log_event( "Display dataset id: %s" % str( data.id ) )
        from galaxy import datatypes #DBTODO REMOVE THIS AT REFACTOR
        if to_ext or isinstance(data.datatype, datatypes.binary.Binary): # Saving the file, or binary file
            if data.extension in composite_extensions:
                return self._archive_composite_dataset( trans, data, **kwd )
            else:
                trans.response.headers['Content-Length'] = int( os.stat( data.file_name ).st_size )
                if not to_ext:
                    to_ext = data.extension
                valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                fname = ''.join(c in valid_chars and c or '_' for c in data.name)[0:150]
                trans.response.set_content_type( "application/octet-stream" ) #force octet-stream so Safari doesn't append mime extensions to filename
                trans.response.headers["Content-Disposition"] = 'attachment; filename="Galaxy%s-[%s].%s"' % (data.hid, fname, to_ext)
                return open( data.file_name )
        if not os.path.exists( data.file_name ):
            raise paste.httpexceptions.HTTPNotFound( "File Not Found (%s)." % data.file_name )
        max_peek_size = 1000000 # 1 MB
        if isinstance(data.datatype, datatypes.images.Html):
            max_peek_size = 10000000 # 10 MB for html
        if not preview or isinstance(data.datatype, datatypes.images.Image) or os.stat( data.file_name ).st_size < max_peek_size:
            if trans.app.config.sanitize_all_html and trans.response.get_content_type() == "text/html":
                # Sanitize anytime we respond with plain text/html content.
                return sanitize_html(open( data.file_name ).read())
            return open( data.file_name )
        else:
            trans.response.set_content_type( "text/html" )
            return trans.stream_template_mako( "/dataset/large_file.mako",
                                            truncated_data = open( data.file_name ).read(max_peek_size),
                                            data = data)

    def display_name(self, dataset):
        """Returns formatted html of dataset name"""
        try:
            if type ( dataset.name ) is unicode:
                return escape( dataset.name )
            else:
                return escape( unicode( dataset.name, 'utf-8 ') )
        except:
            return "name unavailable"
    def display_info(self, dataset):
        """Returns formatted html of dataset info"""
        try:
            # Change new line chars to html
            info = escape( dataset.info )
            if info.find( '\r\n' ) >= 0:
                info = info.replace( '\r\n', '<br/>' )
            if info.find( '\r' ) >= 0:
                info = info.replace( '\r', '<br/>' )
            if info.find( '\n' ) >= 0:
                info = info.replace( '\n', '<br/>' )

            # Convert to unicode to display non-ascii characters.
            if type( info ) is not unicode:
                info = unicode( info, 'utf-8')

            return info
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
    def add_display_app ( self, app_id, label, file_function, links_function ):
        """
        Adds a display app to the datatype.
        app_id is a unique id
        label is the primary display label, e.g., display at 'UCSC'
        file_function is a string containing the name of the function that returns a properly formatted display
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
    def clear_display_apps( self ):
        self.supported_display_apps = {}
    def add_display_application( self, display_application ):
        """New style display applications"""
        assert display_application.id not in self.display_applications, 'Attempted to add a display application twice'
        self.display_applications[ display_application.id ] = display_application
    def get_display_application( self, key, default = None ):
        return self.display_applications.get( key, default )
    def get_display_applications_by_dataset( self, dataset, trans ):
        rval = odict()
        for key, value in self.display_applications.iteritems():
            value = value.filter_by_dataset( dataset, trans )
            if value.links:
                rval[key] = value
        return rval
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
    def get_display_links( self, dataset, type, app, base_url, target_frame='_blank', **kwd ):
        """
        Returns a list of tuples of (name, link) for a particular display type.  No check on
        'access' permissions is done here - if you can view the dataset, you can also save it
        or send it to a destination outside of Galaxy, so Galaxy security restrictions do not
        apply anyway.
        """
        try:
            if type in self.get_display_types():
                return target_frame, getattr ( self, self.supported_display_apps[type]['links_function'] ) ( dataset, type, app, base_url, **kwd )
        except:
            log.exception( 'Function %s is referred to in datatype %s for generating links for type %s, but is not accessible' \
                           % ( self.supported_display_apps[type]['links_function'], self.__class__.__name__, type ) )
        return []
    def get_converter_types(self, original_dataset, datatypes_registry):
        """Returns available converters by type for this dataset"""
        return datatypes_registry.get_converters_by_datatype(original_dataset.ext)
    def find_conversion_destination( self, dataset, accepted_formats, datatypes_registry, **kwd ):
        """Returns ( target_ext, existing converted dataset )"""
        return datatypes_registry.find_conversion_destination_for_dataset_by_extensions( dataset, accepted_formats, **kwd )
    def convert_dataset(self, trans, original_dataset, target_type, return_output=False, visible=True, deps=None, set_output_history=True):
        """This function adds a job to the queue to convert a dataset to another type. Returns a message about success/failure."""
        converter = trans.app.datatypes_registry.get_converter_by_target_type( original_dataset.ext, target_type )

        if converter is None:
            raise Exception( "A converter does not exist for %s to %s." % ( original_dataset.ext, target_type ) )
        #Generate parameter dictionary
        params = {}
        #determine input parameter name and add to params
        input_name = 'input1'
        for key, value in converter.inputs.items():
            if deps and value.name in deps:
                params[value.name] = deps[value.name]
            elif value.type == 'data':
                input_name = key

        params[input_name] = original_dataset
        #Run converter, job is dispatched through Queue
        converted_dataset = converter.execute( trans, incoming=params, set_output_hid=visible, set_output_history=set_output_history)[1]
        if len(params) > 0:
            trans.log_event( "Converter params: %s" % (str(params)), tool_id=converter.id )
        if not visible:
            for name, value in converted_dataset.iteritems():
                value.visible = False
        if return_output:
            return converted_dataset
        return "The file conversion of %s on data %s has been added to the Queue." % (converter.name, original_dataset.hid)
    #We need to clear associated files before we set metadata
    #so that as soon as metadata starts to be set, e.g. implicitly converted datasets are deleted and no longer available 'while' metadata is being set, not just after
    #We'll also clear after setting metadata, for backwards compatibility
    def after_setting_metadata( self, dataset ):
        """This function is called on the dataset after metadata is set."""
        dataset.clear_associated_files( metadata_safe = True )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is set."""
        dataset.clear_associated_files( metadata_safe = True )
    def __new_composite_file( self, name, optional = False, mimetype = None, description = None, substitute_name_with_metadata = None, is_binary = False, space_to_tab = False, **kwds ):
        kwds[ 'name' ] = name
        kwds[ 'optional' ] = optional
        kwds[ 'mimetype' ] = mimetype
        kwds[ 'description' ] = description
        kwds[ 'substitute_name_with_metadata' ] = substitute_name_with_metadata
        kwds[ 'is_binary' ] = is_binary
        kwds[ 'space_to_tab' ] = space_to_tab
        return Bunch( **kwds )
    def add_composite_file( self, name, **kwds ):
        #self.composite_files = self.composite_files.copy()
        self.composite_files[ name ] = self.__new_composite_file( name, **kwds )
    def __substitute_composite_key( self, key, composite_file, dataset = None ):
        if composite_file.substitute_name_with_metadata:
            if dataset:
                meta_value = str( dataset.metadata.get( composite_file.substitute_name_with_metadata ) )
            else:
                meta_value = self.spec[composite_file.substitute_name_with_metadata].default
            return key % meta_value
        return key
    @property
    def writable_files( self, dataset = None ):
        files = odict()
        if self.composite_type != 'auto_primary_file':
            files[ self.primary_file_name ] = self.__new_composite_file( self.primary_file_name )
        for key, value in self.get_composite_files( dataset = dataset ).iteritems():
            files[ key ] = value
        return files
    def get_composite_files( self, dataset = None ):
        def substitute_composite_key( key, composite_file ):
            if composite_file.substitute_name_with_metadata:
                if dataset:
                    meta_value = str( dataset.metadata.get( composite_file.substitute_name_with_metadata ) )
                else:
                    meta_value = self.metadata_spec[ composite_file.substitute_name_with_metadata ].default
                return key % meta_value
            return key
        files = odict()
        for key, value in self.composite_files.iteritems():
            files[ substitute_composite_key( key, value ) ] = value
        return files
    def generate_auto_primary_file( self, dataset = None ):
        raise Exception( "generate_auto_primary_file is not implemented for this datatype." )
    @property
    def has_resolution(self):
        return False



    def merge( split_files, output_file):
        """
        TODO: Do we need to merge gzip files using gzjoin? cat seems to work,
        but might be brittle. Need to revisit this.
        """
        if len(split_files) == 1:
            cmd = 'mv -f %s %s' % ( split_files[0], output_file )
        else:
            cmd = 'cat %s > %s' % ( ' '.join(split_files), output_file )
        result = os.system(cmd)
        if result != 0:
            raise Exception('Result %s from %s' % (result, cmd))
    merge = staticmethod(merge)

class Text( Data ):
    file_ext = 'txt'
    line_class = 'line'

    """Add metadata elements"""
    MetadataElement( name="data_lines", default=0, desc="Number of data lines", readonly=True, optional=True, visible=False, no_value=0 )

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
    def set_meta( self, dataset, **kwd ):
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.data_lines = self.count_data_lines(dataset)
    def estimate_file_lines( self, dataset ):
        """
        Perform a rough estimate by extrapolating number of lines from a small read.
        """
        sample_size = 1048576
        dataset_fh = open( dataset.file_name )
        dataset_read = dataset_fh.read(sample_size)
        dataset_fh.close()
        sample_lines = dataset_read.count('\n')
        est_lines = int(sample_lines * (float(dataset.get_size()) / float(sample_size)))
        return est_lines
    def count_data_lines(self, dataset):
        """
        Count the number of lines of data in dataset,
        skipping all blank lines and comments.
        """
        data_lines = 0
        for line in file( dataset.file_name ):
            line = line.strip()
            if line and not line.startswith( '#' ):
                data_lines += 1
        return data_lines
    def set_peek( self, dataset, line_count=None, is_multi_byte=False, WIDTH=256, skipchars=[] ):
        """
        Set the peek.  This method is used by various subclasses of Text.
        """
        if not dataset.dataset.purged:
            # The file must exist on disk for the get_file_peek() method
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte, WIDTH=WIDTH, skipchars=skipchars )
            if line_count is None:
                # See if line_count is stored in the metadata
                if dataset.metadata.data_lines:
                    dataset.blurb = "%s %s" % ( util.commaify( str(dataset.metadata.data_lines) ), inflector.cond_plural(dataset.metadata.data_lines, self.line_class) )
                else:
                    # Number of lines is not known ( this should not happen ), and auto-detect is
                    # needed to set metadata
                    # This can happen when the file is larger than max_optional_metadata_filesize.
                    if int(dataset.get_size()) <= 1048576:
                        #Small dataset, recount all lines and reset peek afterward.
                        lc = self.count_data_lines(dataset)
                        dataset.metadata.data_lines = lc
                        dataset.blurb = "%s %s" % ( util.commaify( str(lc) ), inflector.cond_plural(lc, self.line_class) )
                    else:
                        est_lines = self.estimate_file_lines(dataset)
                        dataset.blurb = "~%s %s" % ( util.commaify(util.roundify(str(est_lines))), inflector.cond_plural(est_lines, self.line_class) )
            else:
                dataset.blurb = "%s %s" % ( util.commaify( str(line_count) ), inflector.cond_plural(line_count, self.line_class) )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def split( cls, input_datasets, subdir_generator_function, split_params):
        """
        Split the input files by line.
        """
        if split_params is None:
            return

        if len(input_datasets) > 1:
            raise Exception("Text file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        lines_per_file = None
        chunk_size = None
        if split_params['split_mode'] == 'number_of_parts':
            lines_per_file = []
            # Computing the length is expensive!
            def _file_len(fname):
                i = 0
                f = open(fname)
                for i, l in enumerate(f):
                    pass
                f.close()
                return i + 1
            length = _file_len(input_files[0])
            parts = int(split_params['split_size'])
            if length < parts:
                parts = length
            len_each, remainder = divmod(length, parts)
            while length > 0:
                chunk = len_each
                if remainder > 0:
                    chunk += 1
                lines_per_file.append(chunk)
                remainder=- 1
                length -= chunk
        elif split_params['split_mode'] == 'to_size':
            chunk_size = int(split_params['split_size'])
        else:
            raise Exception('Unsupported split mode %s' % split_params['split_mode'])

        f = open(input_files[0], 'rt')
        try:
            chunk_idx = 0
            file_done = False
            part_file = None
            while not file_done:
                if lines_per_file is None:
                    this_chunk_size = chunk_size
                elif chunk_idx < len(lines_per_file):
                    this_chunk_size = lines_per_file[chunk_idx]
                    chunk_idx += 1
                lines_remaining = this_chunk_size
                part_file = None
                while lines_remaining > 0:
                    a_line = f.readline()
                    if a_line == '':
                        file_done = True
                        break
                    if part_file is None:
                        part_dir = subdir_generator_function()
                        part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
                        part_file = open(part_path, 'w')
                    part_file.write(a_line)
                    lines_remaining -= 1
                if part_file is not None:
                    part_file.close()
        except Exception,  e:
            log.error('Unable to split files: %s' % str(e))
            f.close()
            if part_file is not None:
                part_file.close()
            raise
        f.close()
    split = classmethod(split)

class LineCount( Text ):
    """
    Dataset contains a single line with a single integer that denotes the
    line count for a related dataset. Used for custom builds.
    """
    pass

class Newick( Text ):
    pass

# ------------- Utility methods --------------

# nice_size used to be here, but to resolve cyclical dependencies it's been
# moved to galaxy.util.  It belongs there anyway since it's used outside
# datatypes.
nice_size = util.nice_size

def get_test_fname( fname ):
    """Returns test data filename"""
    path, name = os.path.split(__file__)
    full_path = os.path.join( path, 'test', fname )
    return full_path
def get_file_peek( file_name, is_multi_byte=False, WIDTH=256, LINE_COUNT=5, skipchars=[] ):
    """
    Returns the first LINE_COUNT lines wrapped to WIDTH

    ## >>> fname = get_test_fname('4.bed')
    ## >>> get_file_peek(fname)
    ## 'chr22    30128507    31828507    uc003bnx.1_cds_2_0_chr22_29227_f    0    +\n'
    """
    # Set size for file.readline() to a negative number to force it to
    # read until either a newline or EOF.  Needed for datasets with very
    # long lines.
    if WIDTH == 'unlimited':
        WIDTH = -1
    lines = []
    count = 0
    file_type = None
    data_checked = False
    temp = open( file_name, "U" )
    while count <= LINE_COUNT:
        line = temp.readline( WIDTH )
        if line and not is_multi_byte and not data_checked:
            # See if we have a compressed or binary file
            if line[0:2] == util.gzip_magic:
                file_type = 'gzipped'
                break
            else:
                for char in line:
                    if ord( char ) > 128:
                        file_type = 'binary'
                        break
            data_checked = True
        if file_type in [ 'gzipped', 'binary' ]:
            break
        skip_line = False
        for skipchar in skipchars:
            if line.startswith( skipchar ):
                skip_line = True
                break
        if not skip_line:
            lines.append( line )
            count += 1
    temp.close()
    if file_type in [ 'gzipped', 'binary' ]:
        text = "%s file" % file_type
    else:
        try:
            text = unicode( '\n'.join( lines ), 'utf-8' )
        except UnicodeDecodeError:
            text = "binary/unknown file"
    return text

