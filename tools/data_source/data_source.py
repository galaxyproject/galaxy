#!/usr/bin/env python
# Retrieves data from external data source applications and stores in a dataset file.
# Data source application parameters are temporarily stored in the dataset file.
import socket, urllib, sys, os, gzip, tempfile, shutil
from galaxy import eggs
from galaxy.util import gzip_magic

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def check_gzip( filename ):
    # TODO: This needs to check for BAM files since they are compressed and must remain so ( see upload.py )
    temp = open( filename, "U" )
    magic_check = temp.read( 2 )
    temp.close()
    if magic_check != gzip_magic:
        return False
    return True

def __main__():
    filename = sys.argv[1]
    try:
        max_file_size = int( sys.argv[2] )
    except:
        max_file_size = 0
    params = {}
    for line in open( filename, 'r' ):
        try:
            line = line.strip()
            fields = line.split( '\t' )
            params[ fields[0] ] = fields[1]
        except:
            continue
    URL = params.get( 'URL', None )
    if not URL:
        open( filename, 'w' ).write( "" )
        stop_err( 'The remote data source application has not sent back a URL parameter in the request.' )
    URL_method = params.get( 'URL_method', None )
    CHUNK_SIZE = 2**20 # 1Mb
    # The Python support for fetching resources from the web is layered. urllib uses the httplib
    # library, which in turn uses the socket library.  As of Python 2.3 you can specify how long
    # a socket should wait for a response before timing out. By default the socket module has no
    # timeout and can hang. Currently, the socket timeout is not exposed at the httplib or urllib2
    # levels. However, you can set the default timeout ( in seconds ) globally for all sockets by
    # doing the following.
    socket.setdefaulttimeout( 600 )
    # The following calls to urllib2.urlopen() will use the above default timeout
    try:
        if not URL_method or URL_method == 'get':
            page = urllib.urlopen( URL )
        elif URL_method == 'post':
            page = urllib.urlopen( URL, urllib.urlencode( params ) )
    except Exception, e:
        stop_err( 'The remote data source application may be off line, please try again later. Error: %s' % str( e ) )
    if max_file_size:
        file_size = int( page.info().get( 'Content-Length', 0 ) )
        if file_size > max_file_size:
            stop_err( 'The size of the data (%d bytes) you have requested exceeds the maximum allowed (%d bytes) on this server.' % ( file_size, max_file_size ) )
    out = open( filename, 'w' )
    while 1:
        chunk = page.read( CHUNK_SIZE )
        if not chunk:
            break
        out.write( chunk )
    out.close()
    if check_gzip( filename ):
        # TODO: This needs to check for BAM files since they are compressed and must remain so ( see upload.py )
        fd, uncompressed = tempfile.mkstemp()
        gzipped_file = gzip.GzipFile( filename )
        while 1:
            try:
                chunk = gzipped_file.read( CHUNK_SIZE )
            except IOError:
                os.close( fd )
                os.remove( uncompressed )
                gzipped_file.close()
                stop_err( 'Problem uncompressing gzipped data, please try retrieving the data uncompressed.' )
            if not chunk:
                break
            os.write( fd, chunk )
        os.close( fd )
        gzipped_file.close()
        # Replace the gzipped file with the uncompressed file
        shutil.move( uncompressed, filename )        
    
if __name__ == "__main__": __main__()
