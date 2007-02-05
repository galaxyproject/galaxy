"""
Utility functions used systemwide.

"""
import logging
import threading, sets, random, string, md5, re, binascii, pickle, time, datetime, math

import pkg_resources

pkg_resources.require( 'docutils' )
import docutils.core
from galaxy.util.docutils_ext.htmlfrag import Writer as HTMLFragWriter

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree

log   = logging.getLogger(__name__)
_lock = threading.RLock()

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
    >>> len(sets.Set(ids))
    1000
    """
    id  = str( random.getrandbits( KEY_SIZE ) )
    return md5.new(id).hexdigest()

# this sets the browser mime type for special downloads dowloading
mime_types = {
    'png'  : 'image/png', 'gif' : 'image/gif', 'jpg' : 'image/jpeg',
    'html' : 'text/html', 'htm' : 'text/html', 'pdf' : 'application/pdf',
    'gmaj.zip' : 'application/zip',
}

text_types = sets.Set([ 
    'txt', 'text', 'wig', 'genbank', 'motif', 'acedb', 'nexus', 'fitch', 'meganon', 'codata', 'dbmotif', 
    'table', 'fasta', 'txt', 'gff', 'pir', 'ig', 'seqtable', 'clustal', 'gcg', 'hennig86', 'excel', 'asn1', 
    'regions', 'simple', 'score', 'text', 'msf', 'selex', 'tagseq', 'embl', 'srspair', 'staden', 
    'strider', 'xbed', 'markx10', 'pair', 'markx1', 'markx0', 'markx3', 'markx2', 'jackknifer', 
    'ncbi', 'mega', 'fa', 'feattable', 'phylip', 'diffseq', 'bed', 'srs', 'jackknifernon', 'swiss', 
    'phylipnon', 'nexusnon', 'nametable', 'xml', 'interval', 'tabular', 'maf','axt', 'lav', 'laj'
])     

def parse_xml(fname):
    """Returns an parsed xml tree"""
    tree = ElementTree.parse(fname)
    return tree

def xml_to_string(elem):
    """Returns an string from and xml tree"""
    text = ElementTree.tostring(elem)
    return text

# characters that are valid
valid_chars  = sets.Set(string.letters + string.digits + " -=_.()/+*^,:?!")

# characters that are allowed but need to be escaped
mapped_chars = { '>' :'__gt__', 
                 '<' :'__lt__', 
                 "'" :'__sq__',
                 '"' :'__dq__',
                 '[' :'__ob__',
                 ']' :'__cb__',
                 '{' :'__oc__',
                 '}' :'__cc__',
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
    if type(value) == type('x'):
        return sanitize_text(value)
    elif type(value) == type([]):
        return map(sanitize_text, value)
    else:
        raise Exception, 'Unknown parameter type'

class Params:
    """
    Stores and 'sanitizes' parameters. Alphanumeric characters and the  
    non-alpahnumeric ones that are deemed safe are let to pass through (see L{valid_chars}).
    Some non-safe characters are escaped to safe forms for example C{>} becomes C{__lt__} 
    (see L{mapped_chars}). All other characters are replaced with C{X}.
    
    Operates on string or list values only (HTTP parameters).
    
    >>> values = { 'status':'on', 'symbols':[  'alpha', '<>', '$rm&#@!' ]  }
    >>> par = Params(values)
    >>> par.status
    'on'
    >>> par.value == None      # missing attributes return None
    True
    >>> par.get('price', 0)
    0
    >>> par.symbols            # replaces unknown symbols with X
    ['alpha', '__lt____gt__', 'XrmXXX!']
    >>> par.flatten()          # flattening to a list
    [('status', 'on'), ('symbols', 'alpha'), ('symbols', '__lt____gt__'), ('symbols', 'XrmXXX!')]
    """
    
    # HACK: Need top prevent sanitizing certain parameter types. The 
    #       better solution I think is to more responsibility for 
    #       sanitizing into the tool parameters themselves so that
    #       different parameters can be sanitized in different ways.
    NEVER_SANITIZE = ['file_data', 'url_paste', 'URL']
    
    def __init__(self, params, safe=True):
        if safe:
            for key, value in params.items():
                if key not in self.NEVER_SANITIZE:
                    self.__dict__[key] = sanitize_param(value)
                else:
                    self.__dict__[key] = value
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
    if string.lower() in ( 'true', 'yes', 'on' ):
        return True
    else:
        return False

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

#Read build names from file, this list is also used in upload tool
dbnames = []
try:
    for line in open("static/ucsc/builds.txt"):
        try:
            if line[0:1] == "#": continue
            fields = line.replace("\r","").replace("\n","").split("\t")
            #Special case of unspecified build is at top of list
            if fields[0] == "?":
                dbnames.insert(0,(fields[0],fields[1]))
                continue
            #Alphabetize build list
            for i in range(0,len(dbnames)):
                if dbnames[i][0] == "?": continue
                if dbnames[i][1] > fields[1]:
                    dbnames.insert(i,(fields[0],fields[1]))
                    break
            else:
                dbnames.append( (fields[0],fields[1]) )
        except: continue
except:
    print "ERROR: Unable to read builds file"
if len(dbnames)<1:
    dbnames = [('?', 'unspecified (?)')]
    
    
#read db names to ucsc mappings from file, this file should probably be merged with the one above
ucsc_build_sites= []
try:
    for line in open("static/ucsc/ucsc_build_sites.txt"):
        try:
            if line[0:1] == "#": continue
            fields = line.replace("\r","").replace("\n","").split("\t")
            site_name = fields[0]
            site = fields[1]
            site_builds = fields[2].split(",")
            site_dict = {'name':site_name, 'url':site, 'builds':site_builds}
            ucsc_build_sites.append( site_dict )
        except: continue
except:
    print "ERROR: Unable to read builds to ucsc site file"

    
if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__], verbose=False)
