#!/usr/bin/env python
#Retreives data from UCSC and stores in a file. UCSC parameters are provided in the input/output file.
import urllib, sys, os, gzip, tempfile, shutil
from galaxy import eggs
#from galaxy.datatypes import data
from galaxy.util import gzip_magic

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def check_gzip( filename ):
    temp = open( filename, "U" )
    magic_check = temp.read( 2 )
    temp.close()
    if magic_check != gzip_magic:
        return False
    return True

def __main__():
    filename = sys.argv[1]
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
    out = open( filename, 'w' )
    CHUNK_SIZE = 2**20 # 1Mb 
    try:
        if not URL_method or URL_method == 'get':
            page = urllib.urlopen( URL )
        elif URL_method == 'post':
            page = urllib.urlopen( URL, urllib.urlencode( params ) )
    except:
        stop_err( 'It appears that the remote data source application is currently off line. Please try again later.' )
    while 1:
        chunk = page.read( CHUNK_SIZE )
        if not chunk:
            break
        out.write( chunk )
    out.close()
    if check_gzip( filename ):
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
