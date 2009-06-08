"""
Utility functions used systemwide.

"""
import logging
import threading, random, string, re, binascii, pickle, time, datetime, math, re, os, sys

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

import pkg_resources

pkg_resources.require( 'docutils' )
import docutils.core
from galaxy.util.docutils_ext.htmlfrag import Writer as HTMLFragWriter

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree

pkg_resources.require( "wchartype" )
import wchartype

log   = logging.getLogger(__name__)
_lock = threading.RLock()

gzip_magic = '\037\213'

def is_multi_byte( chars ):
    for char in chars:
        try:
            char = unicode( char )
        except UnicodeDecodeError, e:
            # Probably binary
            return False
        if wchartype.is_asian( char ) or \
            wchartype.is_full_width( char ) or \
            wchartype.is_kanji( char ) or \
            wchartype.is_hiragana( char ) or \
            wchartype.is_katakana( char ) or \
            wchartype.is_half_katakana( char ) or \
            wchartype.is_hangul( char ) or \
            wchartype.is_full_digit( char ) or \
            wchartype.is_full_letter( char ):
            return True
    return False

def synchronized(func):
    """This wrapper will serialize access to 'func' to a single thread. Use it as a decorator."""
    def caller(*params, **kparams):
        _lock.acquire(True) # Wait
        try:
            return func(*params, **kparams)
        finally:
            _lock.release()
    return caller

def file_iter(fname, sep=None):
    """
    This generator iterates over a file and yields its lines 
    splitted via the C{sep} parameter. Skips empty lines and lines starting with 
    the C{#} character.
    
    >>> lines = [ line for line in file_iter(__file__) ]
    >>> len(lines) !=  0 
    True
    """
    for line in file(fname):
        if line and line[0] != '#':
            yield line.split(sep)

def file_reader(fp, chunk_size=65536):
    """This generator yields the open fileobject in chunks (default 64k). Closes the file at the end"""
    while 1:
        data = fp.read(chunk_size)
        if not data:
            break
        yield data
    fp.close()

def unique_id(KEY_SIZE=128):
    """
    Genenerates a unique ids
    
    >>> ids = [ unique_id() for i in range(1000) ]
    >>> len(set(ids))
    1000
    """
    id  = str( random.getrandbits( KEY_SIZE ) )
    return md5(id).hexdigest()

def parse_xml(fname):
    """Returns an parsed xml tree"""
    tree = ElementTree.parse(fname)
    return tree

def xml_to_string(elem):
    """Returns an string from and xml tree"""
    text = ElementTree.tostring(elem)
    return text

# characters that are valid
valid_chars  = set(string.letters + string.digits + " -=_.()/+*^,:?!")

# characters that are allowed but need to be escaped
mapped_chars = { '>' :'__gt__', 
                 '<' :'__lt__', 
                 "'" :'__sq__',
                 '"' :'__dq__',
                 '[' :'__ob__',
                 ']' :'__cb__',
                 '{' :'__oc__',
                 '}' :'__cc__',
                 '@' : '__at__'
                 }

def restore_text(text):
    """Restores sanitized text"""
    for key, value in mapped_chars.items():
        text = text.replace(value, key)
    return text

def sanitize_text(text):
    """Restricts the characters that are allowed in a text"""
    out = []
    for c in text:
        if c in valid_chars:
            out.append(c)
        elif c in mapped_chars:
            out.append(mapped_chars[c])
        else:
            out.append('X') # makes debugging easier
    return ''.join(out)

def sanitize_param(value):
    """Clean incoming parameters (strings or lists)"""
    if isinstance( value, basestring ):
        return sanitize_text(value)
    elif isinstance( value, list ):
        return map(sanitize_text, value)
    else:
        print value
        raise Exception, 'Unknown parameter type (%s)' % ( type( value ) )

class Params:
    """
    Stores and 'sanitizes' parameters. Alphanumeric characters and the  
    non-alpahnumeric ones that are deemed safe are let to pass through (see L{valid_chars}).
    Some non-safe characters are escaped to safe forms for example C{>} becomes C{__lt__} 
    (see L{mapped_chars}). All other characters are replaced with C{X}.
    
    Operates on string or list values only (HTTP parameters).
    
    >>> values = { 'status':'on', 'symbols':[  'alpha', '<>', '$rm&#!' ]  }
    >>> par = Params(values)
    >>> par.status
    'on'
    >>> par.value == None      # missing attributes return None
    True
    >>> par.get('price', 0)
    0
    >>> par.symbols            # replaces unknown symbols with X
    ['alpha', '__lt____gt__', 'XrmXX!']
    >>> par.flatten()          # flattening to a list
    [('status', 'on'), ('symbols', 'alpha'), ('symbols', '__lt____gt__'), ('symbols', 'XrmXX!')]
    """
    
    # HACK: Need top prevent sanitizing certain parameter types. The 
    #       better solution I think is to more responsibility for 
    #       sanitizing into the tool parameters themselves so that
    #       different parameters can be sanitized in different ways.
    NEVER_SANITIZE = ['file_data', 'url_paste', 'URL']
    
    def __init__( self, params, safe=True, sanitize=True, tool=None ):
        if safe:
            for key, value in params.items():
                # Check to see if we should translate certain parameter names.  For example,
                # in data_source tools, the external data source application may send back 
                # parameter names like GENOME which is translated to dbkey in Galaxy.
                # param_trans_dict looks like { "GENOME" : [ "dbkey" "?" ] }
                new_key = key
                new_value = value
                if tool and tool.tool_type == 'data_source':
                    if key in tool.param_trans_dict:
                        new_key = tool.param_trans_dict[ key ][0]
                        if new_key == 'data_type':
                            try:
                                # The Galaxy "data_type entry is special in that it can include the ability
                                # to translate the format to a Galaxy supported format.  In the dict, this entry
                                # looks something like:  
                                # {'hgta_outputType': ['data_type', 'bed', {'selectedFields': 'tabular'}] }
                                format_trans_dict = tool.param_trans_dict[ key ][2]
                                if value in format_trans_dict:
                                    new_value = format_trans_dict[ value ]
                            except:
                                pass
                        elif new_key == 'URL':
                            # As above, the URL can include a set of params from the remote data source
                            # that must be appended to the URL prior to the post.  In this case, the
                            # dict entry would look something like:
                            # ['URL', '', {'q': '', 's': '', 'd': '', 'dbkey': '', 't': ''}]
                            try:
                                add_to_url_dict = tool.param_trans_dict[ key ][2]
                                if new_value.count( '?' ) == 0:
                                    sep = '?'
                                else:
                                    sep = '&'
                                for param_name, missing_value in add_to_url_dict.items():
                                    param_value = params.get( param_name, None )
                                    if not param_value and missing_value:
                                        param_value = missing_value
                                    if param_value:
                                        new_value += '%s%s=%s' % ( sep, param_name, param_value )
                                        sep = '&'
                            except:
                                pass
                        if not value and not new_value:
                            new_value = tool.param_trans_dict[ key ][1]
                if sanitize and not ( key in self.NEVER_SANITIZE or True in [ key.endswith( "|%s" % nonsanitize_parameter ) for nonsanitize_parameter in self.NEVER_SANITIZE ] ): #sanitize check both ungrouped and grouped parameters by name
                    self.__dict__[ new_key ] = sanitize_param( new_value )
                else:
                    self.__dict__[ new_key ] = new_value
            if tool and tool.tool_type == 'data_source':
                # Add the tool's URL_method to params
                self.__dict__[ 'URL_method' ] = tool.URL_method
                for key, value in tool.param_trans_dict.items():
                    # Make sure that all translated values used in Galaxy are added to the params
                    galaxy_name = tool.param_trans_dict[ key ][0]
                    if galaxy_name not in self.__dict__:
                        # This will set the galaxy_name to the "missing" value
                        self.__dict__[ galaxy_name ] = tool.param_trans_dict[ key ][1]
        else:
            self.__dict__.update(params)

    def flatten(self):
        """
        Creates a tuple list from a dict with a tuple/value pair for every value that is a list
        """
        flat = []
        for key, value in self.__dict__.items():
            if type(value) == type([]):
                for v in value:
                    flat.append( (key, v) )
            else:
                flat.append( (key, value) )
        return flat

    def __getattr__(self, name):
        """This is here to ensure that we get None for non existing parameters"""
        return None 
    
    def get(self, key, default):
        return self.__dict__.get(key, default)
    
    def __str__(self):
        return '%s' % self.__dict__

    def __len__(self):
        return len(self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def update(self, values):
        self.__dict__.update(values)

def rst_to_html( s ):
    """Convert a blob of reStructuredText to HTML"""
    log = logging.getLogger( "docutils" )
    class FakeStream( object ):
        def write( self, str ):
            if len( str ) > 0 and not str.isspace():
                log.warn( str )
    return docutils.core.publish_string( s, writer=HTMLFragWriter(), settings_overrides=dict( warning_stream=FakeStream() ) )

def xml_text(root, name):
    """Returns the text inside an element"""
    # Try attribute first
    val = root.get(name)
    if val: return val
    # Then try as element
    elem = root.find(name)    
    if elem is not None and elem.text:
        text = ''.join(elem.text.splitlines())
        return text.strip()
    # No luck, return empty string
    return ''
    
def string_as_bool( string ):
    if str( string ).lower() in ( 'true', 'yes', 'on' ):
        return True
    else:
        return False

def listify( item ):
    """
    Make a single item a single item list, or return a list if passed a
    list.  Passing a None returns an empty list.
    """
    if not item:
        return []
    elif isinstance( item, list ):
        return item
    elif isinstance( item, basestring ) and item.count( ',' ):
        return item.split( ',' )
    else:
        return [ item ]

def commaify(amount):
    orig = amount
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', amount)
    if orig == new:
        return new
    else:
        return commaify(new)
  
def object_to_string( obj ):
    return binascii.hexlify( pickle.dumps( obj, 2 ) )
    
def string_to_object( s ):
    return pickle.loads( binascii.unhexlify( s ) )
        

def get_ucsc_by_build(build):
    sites = []
    for site in ucsc_build_sites:
        if build in site['builds']:
            sites.append((site['name'],site['url']))
    return sites

def get_gbrowse_sites_by_build(build):
    sites = []
    for site in gbrowse_build_sites:
        if build in site['builds']:
            sites.append((site['name'],site['url']))
    return sites

def read_dbnames(filename):
    """ Read build names from file """
    class DBNames( list ):
        default_value = "?"
        default_name = "unspecified (?)"
    db_names = DBNames()
    try:
        ucsc_builds = {}
        man_builds = [] #assume these are integers
        name_to_db_base = {}
        for line in open(filename):
            try:
                if line[0:1] == "#": continue
                fields = line.replace("\r","").replace("\n","").split("\t")
                #Special case of unspecified build is at top of list
                if fields[0] == "?":
                    db_names.insert(0,(fields[0],fields[1]))
                    continue
                try: #manual build (i.e. microbes)
                    int(fields[0])
                    man_builds.append((fields[1], fields[0]))
                except: #UCSC build
                    db_base = fields[0].rstrip('0123456789')
                    if db_base not in ucsc_builds:
                        ucsc_builds[db_base] = []
                        name_to_db_base[fields[1]] = db_base
                    #we want to sort within a species numerically by revision number
                    build_rev = re.compile(r'\d+$')
                    try: build_rev = int(build_rev.findall(fields[0])[0])
                    except: build_rev = 0
                    ucsc_builds[db_base].append((build_rev, fields[0],fields[1]))
            except: continue
        sort_names = name_to_db_base.keys()
        sort_names.sort()
        for name in sort_names:
            db_base = name_to_db_base[name]
            ucsc_builds[db_base].sort()
            ucsc_builds[db_base].reverse()
            ucsc_builds[db_base] = [(build, name) for build_rev, build, name in ucsc_builds[db_base]]
            db_names = DBNames( db_names + ucsc_builds[db_base] )
        if len( db_names ) > 1 and len( man_builds ) > 0: db_names.append( ( db_names.default_value, '----- Additional Species Are Below -----' ) )
        man_builds.sort()
        man_builds = [(build, name) for name, build  in man_builds]
        db_names = DBNames( db_names + man_builds )
    except Exception, e:
        print "ERROR: Unable to read builds file:", e
    if len(db_names)<1:
        db_names = DBNames( [( db_names.default_value,  db_names.default_name )] )
    return db_names

def read_build_sites(filename):
    """ read db names to ucsc mappings from file, this file should probably be merged with the one above """
    build_sites = []
    try:
        for line in open(filename):
            try:
                if line[0:1] == "#": continue
                fields = line.replace("\r","").replace("\n","").split("\t")
                site_name = fields[0]
                site = fields[1]
                site_builds = fields[2].split(",")
                site_dict = {'name':site_name, 'url':site, 'builds':site_builds}
                build_sites.append( site_dict )
            except: continue
    except:
        print "ERROR: Unable to read builds for site file %s" %filename
    return build_sites

def relpath( path, start = None ):
    """Return a relative version of a path"""
    #modified from python 2.6.1 source code
    
    #version 2.6+ has it built in, we'll use the 'official' copy
    if sys.version_info[:2] >= ( 2, 6 ):
        if start is not None:
            return os.path.relpath( path, start )
        return os.path.relpath( path )
    
    #we need to initialize some local parameters
    curdir = os.curdir
    pardir = os.pardir
    sep = os.sep
    commonprefix = os.path.commonprefix
    join = os.path.join
    if start is None:
        start = curdir
    
    #below is the unedited (but formated) relpath() from posixpath.py of 2.6.1
    #this will likely not function properly on non-posix systems, i.e. windows
    if not path:
        raise ValueError( "no path specified" )
    
    start_list = os.path.abspath( start ).split( sep )
    path_list = os.path.abspath( path ).split( sep )
    
    # Work out how much of the filepath is shared by start and path.
    i = len( commonprefix( [ start_list, path_list ] ) )
    
    rel_list = [ pardir ] * ( len( start_list )- i ) + path_list[ i: ]
    if not rel_list:
        return curdir
    return join( *rel_list )

def stringify_dictionary_keys( in_dict ):
    #returns a new dictionary
    #changes unicode keys into strings, only works on top level (does not recurse)
    #unicode keys are not valid for expansion into keyword arguments on method calls
    out_dict = {}
    for key, value in in_dict.iteritems():
        out_dict[ str( key ) ] = value
    return out_dict

galaxy_root_path = os.path.join(__path__[0], "..","..","..")
dbnames = read_dbnames( os.path.join( galaxy_root_path, "tool-data", "shared", "ucsc", "builds.txt" ) ) #this list is used in edit attributes and the upload tool
ucsc_build_sites = read_build_sites( os.path.join( galaxy_root_path, "tool-data", "shared", "ucsc", "ucsc_build_sites.txt" ) ) #this list is used in history.tmpl
gbrowse_build_sites = read_build_sites( os.path.join( galaxy_root_path, "tool-data", "shared", "gbrowse", "gbrowse_build_sites.txt" ) ) #this list is used in history.tmpl

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__], verbose=False)
