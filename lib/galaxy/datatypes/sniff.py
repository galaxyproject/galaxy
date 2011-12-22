"""
File format detector
"""
import logging, sys, os, csv, tempfile, shutil, re, zipfile, gzip
import registry
from galaxy import util
from galaxy.datatypes.checkers import *
from galaxy.datatypes.binary import unsniffable_binary_formats

log = logging.getLogger(__name__)
        
def get_test_fname(fname):
    """Returns test data filename"""
    path, name = os.path.split(__file__)
    full_path = os.path.join(path, 'test', fname)
    return full_path

def stream_to_open_named_file( stream, fd, filename ):
    """Writes a stream to the provided file descriptor, returns the file's name and bool( is_multi_byte ). Closes file descriptor"""
    #signature and behavor is somewhat odd, due to backwards compatibility, but this can/should be done better
    CHUNK_SIZE = 1048576
    data_checked = False
    is_compressed = False
    is_binary = False
    is_multi_byte = False
    while 1:
        chunk = stream.read( CHUNK_SIZE )
        if not chunk:
            break
        if not data_checked:
            # See if we're uploading a compressed file
            if zipfile.is_zipfile( filename ):
                is_compressed = True
            else:
                try:
                    if unicode( chunk[:2] ) == unicode( util.gzip_magic ):
                        is_compressed = True
                except:
                    pass
            if not is_compressed:
                # See if we have a multi-byte character file
                chars = chunk[:100]
                is_multi_byte = util.is_multi_byte( chars )
                if not is_multi_byte:
                    for char in chars:
                        if ord( char ) > 128:
                            is_binary = True
                            break
            data_checked = True
        if not is_compressed and not is_binary:
            os.write( fd, chunk.encode( "utf-8" ) )
        else:
            # Compressed files must be encoded after they are uncompressed in the upload utility,
            # while binary files should not be encoded at all.
            os.write( fd, chunk )
    os.close( fd )
    return filename, is_multi_byte

def stream_to_file( stream, suffix='', prefix='', dir=None, text=False ):
    """Writes a stream to a temporary file, returns the temporary file's name"""
    fd, temp_name = tempfile.mkstemp( suffix=suffix, prefix=prefix, dir=dir, text=text )
    return stream_to_open_named_file( stream, fd, temp_name )

def check_newlines( fname, bytes_to_read=52428800 ):
    """
    Determines if there are any non-POSIX newlines in the first
    number_of_bytes (by default, 50MB) of the file.
    """
    CHUNK_SIZE = 2 ** 20
    f = open( fname, 'r' )
    for chunk in f.read( CHUNK_SIZE ):
        if f.tell() > bytes_to_read:
            break
        if chunk.count( '\r' ):
            f.close()
            return True
    f.close()
    return False

def convert_newlines( fname, in_place=True ):
    """
    Converts in place a file from universal line endings 
    to Posix line endings.

    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("1 2\\r3 4")
    >>> convert_newlines(fname)
    (2, None)
    >>> file(fname).read()
    '1 2\\n3 4\\n'
    """
    fd, temp_name = tempfile.mkstemp()
    fp = os.fdopen( fd, "wt" )
    for i, line in enumerate( file( fname, "U" ) ):
        fp.write( "%s\n" % line.rstrip( "\r\n" ) )
    fp.close()
    if in_place:
        shutil.move( temp_name, fname )
        # Return number of lines in file.
        return ( i + 1, None )
    else:
        return ( i + 1, temp_name )

def sep2tabs( fname, in_place=True, patt="\\s+" ):
    """
    Transforms in place a 'sep' separated file to a tab separated one

    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("1 2\\n3 4\\n")
    >>> sep2tabs(fname)
    (2, None)
    >>> file(fname).read()
    '1\\t2\\n3\\t4\\n'
    """
    regexp = re.compile( patt )
    fd, temp_name = tempfile.mkstemp()
    fp = os.fdopen( fd, "wt" )
    for i, line in enumerate( file( fname ) ):
        line  = line.rstrip( '\r\n' )
        elems = regexp.split( line )
        fp.write( "%s\n" % '\t'.join( elems ) )
    fp.close()
    if in_place:
        shutil.move( temp_name, fname )
        # Return number of lines in file.
        return ( i + 1, None )
    else:
        return ( i + 1, temp_name )

def convert_newlines_sep2tabs( fname, in_place=True, patt="\\s+" ):
    """
    Combines above methods: convert_newlines() and sep2tabs()
    so that files do not need to be read twice

    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("1 2\\r3 4")
    >>> convert_newlines_sep2tabs(fname)
    (2, None)
    >>> file(fname).read()
    '1\\t2\\n3\\t4\\n'
    """
    regexp = re.compile( patt )
    fd, temp_name = tempfile.mkstemp()
    fp = os.fdopen( fd, "wt" )
    for i, line in enumerate( file( fname, "U" ) ):
        line  = line.rstrip( '\r\n' )
        elems = regexp.split( line )
        fp.write( "%s\n" % '\t'.join( elems ) )
    fp.close()
    if in_place:
        shutil.move( temp_name, fname )
        # Return number of lines in file.
        return ( i + 1, None )
    else:
        return ( i + 1, temp_name )

def get_headers( fname, sep, count=60, is_multi_byte=False ):
    """
    Returns a list with the first 'count' lines split by 'sep'
    
    >>> fname = get_test_fname('complete.bed')
    >>> get_headers(fname,'\\t')
    [['chr7', '127475281', '127491632', 'NM_000230', '0', '+', '127486022', '127488767', '0', '3', '29,172,3225,', '0,10713,13126,'], ['chr7', '127486011', '127488900', 'D49487', '0', '+', '127486022', '127488767', '0', '2', '155,490,', '0,2399']]
    """
    headers = []
    for idx, line in enumerate(file(fname)):
        line = line.rstrip('\n\r')
        if is_multi_byte:
            # TODO: fix this - sep is never found in line
            line = unicode( line, 'utf-8' )
            sep = sep.encode( 'utf-8' )
        headers.append( line.split(sep) )
        if idx == count:
            break
    return headers
    
def is_column_based( fname, sep='\t', skip=0, is_multi_byte=False ):
    """
    Checks whether the file is column based with respect to a separator 
    (defaults to tab separator).
    
    >>> fname = get_test_fname('test.gff')
    >>> is_column_based(fname)
    True
    >>> fname = get_test_fname('test_tab.bed')
    >>> is_column_based(fname)
    True
    >>> is_column_based(fname, sep=' ')
    False
    >>> fname = get_test_fname('test_space.txt')
    >>> is_column_based(fname)
    False
    >>> is_column_based(fname, sep=' ')
    True
    >>> fname = get_test_fname('test_ensembl.tab')
    >>> is_column_based(fname)
    True
    >>> fname = get_test_fname('test_tab1.tabular')
    >>> is_column_based(fname, sep=' ', skip=0)
    False
    >>> fname = get_test_fname('test_tab1.tabular')
    >>> is_column_based(fname)
    True
    """
    headers = get_headers( fname, sep, is_multi_byte=is_multi_byte )
    count = 0
    if not headers:
        return False
    for hdr in headers[skip:]:
        if hdr and hdr[0] and not hdr[0].startswith('#'):
            if len(hdr) > 1:
                count = len(hdr)
            break
    if count < 2:
        return False
    for hdr in headers[skip:]:
        if hdr and hdr[0] and not hdr[0].startswith('#'):
            if len(hdr) != count:
                return False
    return True

def guess_ext( fname, sniff_order=None, is_multi_byte=False ):
    """
    Returns an extension that can be used in the datatype factory to
    generate a data for the 'fname' file

    >>> fname = get_test_fname('megablast_xml_parser_test1.blastxml')
    >>> guess_ext(fname)
    'blastxml'
    >>> fname = get_test_fname('interval.interval')
    >>> guess_ext(fname)
    'interval'
    >>> fname = get_test_fname('interval1.bed')
    >>> guess_ext(fname)
    'bed'
    >>> fname = get_test_fname('test_tab.bed')
    >>> guess_ext(fname)
    'bed'
    >>> fname = get_test_fname('sequence.maf')
    >>> guess_ext(fname)
    'maf'
    >>> fname = get_test_fname('sequence.fasta')
    >>> guess_ext(fname)
    'fasta'
    >>> fname = get_test_fname('file.html')
    >>> guess_ext(fname)
    'html'
    >>> fname = get_test_fname('test.gtf')
    >>> guess_ext(fname)
    'gtf'
    >>> fname = get_test_fname('test.gff')
    >>> guess_ext(fname)
    'gff'
    >>> fname = get_test_fname('gff_version_3.gff')
    >>> guess_ext(fname)
    'gff3'
    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("a\\t2\\nc\\t1\\nd\\t0")
    >>> guess_ext(fname)
    'tabular'
    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("a 1 2 x\\nb 3 4 y\\nc 5 6 z")
    >>> guess_ext(fname)
    'txt'
    >>> fname = get_test_fname('test_tab1.tabular')
    >>> guess_ext(fname)
    'tabular'
    >>> fname = get_test_fname('alignment.lav')
    >>> guess_ext(fname)
    'lav'
    >>> fname = get_test_fname('1.sff')
    >>> guess_ext(fname)
    'sff'
    >>> fname = get_test_fname('1.bam')
    >>> guess_ext(fname)
    'bam'
    >>> fname = get_test_fname('3unsorted.bam')
    >>> guess_ext(fname)
    'bam'
    """
    if sniff_order is None:
        datatypes_registry = registry.Registry()
        datatypes_registry.load_datatypes()
        sniff_order = datatypes_registry.sniff_order
    for datatype in sniff_order:
        """
        Some classes may not have a sniff function, which is ok.  In fact, the
        Tabular and Text classes are 2 examples of classes that should never have
        a sniff function.  Since these classes are default classes, they contain 
        few rules to filter out data of other formats, so they should be called
        from this function after all other datatypes in sniff_order have not been
        successfully discovered.
        """
        try:
            if datatype.sniff( fname ):
                return datatype.file_ext
        except:
            pass
    headers = get_headers( fname, None )
    is_binary = False
    if is_multi_byte:
        is_binary = False
    else:
        for hdr in headers:
            for char in hdr:
                if len( char ) > 1:
                    for c in char:
                        if ord( c ) > 128:
                            is_binary = True
                            break
                elif ord( char ) > 128:
                    is_binary = True
                    break
                if is_binary:
                    break
            if is_binary:
                break
    if is_binary:
        return 'data'        #default binary data type file extension
    if is_column_based( fname, '\t', 1, is_multi_byte=is_multi_byte ):
        return 'tabular'    #default tabular data type file extension
    return 'txt'            #default text data type file extension

def handle_compressed_file( filename, datatypes_registry, ext = 'auto' ):
    CHUNK_SIZE = 2**20 # 1Mb
    is_compressed = False
    compressed_type = None
    keep_compressed = False
    is_valid = False
    for compressed_type, check_compressed_function in COMPRESSION_CHECK_FUNCTIONS:
        is_compressed = check_compressed_function( filename )
        if is_compressed:
            break #found compression type
    if is_compressed: 
        if ext in AUTO_DETECT_EXTENSIONS:
            check_exts = COMPRESSION_DATATYPES[ compressed_type ]
        elif ext in COMPRESSED_EXTENSIONS:
            check_exts = [ ext ]
        else:
            check_exts = []
        for compressed_ext in check_exts:
            compressed_datatype = datatypes_registry.get_datatype_by_extension( compressed_ext )
            if compressed_datatype.sniff( filename ):
                ext = compressed_ext
                keep_compressed = True
                is_valid = True
                break
    
    if not is_compressed:
        is_valid = True
    elif not keep_compressed:
        is_valid = True
        fd, uncompressed = tempfile.mkstemp()
        compressed_file = DECOMPRESSION_FUNCTIONS[ compressed_type ]( filename )
        while True:
            try:
                chunk = compressed_file.read( CHUNK_SIZE )
            except IOError, e:
                os.close( fd )
                os.remove( uncompressed )
                compressed_file.close()
                raise IOError, 'Problem uncompressing %s data, please try retrieving the data uncompressed: %s' % ( compressed_type, e )
            if not chunk:
                break
            os.write( fd, chunk )
        os.close( fd )
        compressed_file.close()
        # Replace the compressed file with the uncompressed file
        shutil.move( uncompressed, filename )
    return is_valid, ext

def handle_uploaded_dataset_file( filename, datatypes_registry, ext = 'auto', is_multi_byte = False ):
    is_valid, ext = handle_compressed_file( filename, datatypes_registry, ext = ext )
    
    if not is_valid:
        raise InappropriateDatasetContentError, 'The compressed uploaded file contains inappropriate content.'
    
    if ext in AUTO_DETECT_EXTENSIONS:
        ext = guess_ext( filename, sniff_order = datatypes_registry.sniff_order, is_multi_byte=is_multi_byte )
    
    if check_binary( filename ):
        if ext not in unsniffable_binary_formats and not datatypes_registry.get_datatype_by_extension( ext ).sniff( filename ):
            raise InappropriateDatasetContentError, 'The binary uploaded file contains inappropriate content.'
    elif check_html( filename ):
        raise InappropriateDatasetContentError, 'The uploaded file contains inappropriate HTML content.'
    return ext

AUTO_DETECT_EXTENSIONS = [ 'auto' ] #should 'data' also cause auto detect?
DECOMPRESSION_FUNCTIONS = dict( gzip = gzip.GzipFile )
COMPRESSION_CHECK_FUNCTIONS = [ ( 'gzip', is_gzip ) ]
COMPRESSION_DATATYPES = dict( gzip = [ 'bam' ] )
COMPRESSED_EXTENSIONS = []
for exts in COMPRESSION_DATATYPES.itervalues(): COMPRESSED_EXTENSIONS.extend( exts )

class InappropriateDatasetContentError( Exception ):
    pass

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
