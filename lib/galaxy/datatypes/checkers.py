import os, gzip, re, gzip, zipfile, binascii, bz2, imghdr
from galaxy import util

try:
    import Image as PIL
except ImportError:
    try:
        from PIL import Image as PIL
    except:
        PIL = None

def check_image( file_path ):
    if PIL != None:
        try:
            im = PIL.open( file_path )
        except:
            return False
        if im:
            return im
        return False
    else:
        if imghdr.what( file_path ) != None:
            return True
        return False

def check_html( file_path, chunk=None ):
    if chunk is None:
        temp = open( file_path, "U" )
    else:
        temp = chunk
    regexp1 = re.compile( "<A\s+[^>]*HREF[^>]+>", re.I )
    regexp2 = re.compile( "<IFRAME[^>]*>", re.I )
    regexp3 = re.compile( "<FRAMESET[^>]*>", re.I )
    regexp4 = re.compile( "<META[^>]*>", re.I )
    regexp5 = re.compile( "<SCRIPT[^>]*>", re.I )
    lineno = 0
    for line in temp:
        lineno += 1
        matches = regexp1.search( line ) or regexp2.search( line ) or regexp3.search( line ) or regexp4.search( line ) or regexp5.search( line )
        if matches:
            if chunk is None:
                temp.close()
            return True
        if lineno > 100:
            break
    if chunk is None:
        temp.close()
    return False

def check_binary( name, file_path=True ):
    # Handles files if file_path is True or text if file_path is False
    is_binary = False
    if file_path:
        temp = open( name, "U" )
    else:
        temp = name
    chars_read = 0
    for chars in temp:
        for char in chars:
            chars_read += 1
            if ord( char ) > 128:
                is_binary = True
                break
            if chars_read > 100:
                break
        if chars_read > 100:
            break
    if file_path:
        temp.close()
    return is_binary

def check_gzip( file_path ):
    # This method returns a tuple of booleans representing ( is_gzipped, is_valid )
    # Make sure we have a gzipped file
    try:
        temp = open( file_path, "U" )
        magic_check = temp.read( 2 )
        temp.close()
        if magic_check != util.gzip_magic:
            return ( False, False )
    except:
        return ( False, False )
    # We support some binary data types, so check if the compressed binary file is valid
    # If the file is Bam, it should already have been detected as such, so we'll just check
    # for sff format.
    try:
        header = gzip.open( file_path ).read(4)
        if binascii.b2a_hex( header ) == binascii.hexlify( '.sff' ):
            return ( True, True )
    except:
        return( False, False )
    CHUNK_SIZE = 2**15 # 32Kb
    gzipped_file = gzip.GzipFile( file_path, mode='rb' )
    chunk = gzipped_file.read( CHUNK_SIZE )
    gzipped_file.close()
    # See if we have a compressed HTML file
    if check_html( file_path, chunk=chunk ):
        return ( True, False )
    return ( True, True )

def check_bz2( file_path ):
    try:
        temp = open( file_path, "U" )
        magic_check = temp.read( 3 )
        temp.close()
        if magic_check != util.bz2_magic:
            return ( False, False )
    except:
        return( False, False )
    CHUNK_SIZE = 2**15 # reKb
    bzipped_file = bz2.BZ2File( file_path, mode='rb' )
    chunk = bzipped_file.read( CHUNK_SIZE )
    bzipped_file.close()
    # See if we have a compressed HTML file
    if check_html( file_path, chunk=chunk ):
        return ( True, False )
    return ( True, True )

def check_zip( file_path ):
    if zipfile.is_zipfile( file_path ):
        return True
    return False

def is_bz2( file_path ):
    is_bz2, is_valid = check_bz2( file_path )
    return is_bz2

def is_gzip( file_path ):
    is_gzipped, is_valid = check_gzip( file_path )
    return is_gzipped
