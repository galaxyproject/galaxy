#!/usr/bin/env python2.4
#Retreives data from UCSC and stores in a file. UCSC parameters are provided in the input/output file.
import urllib, sys, os, gzip, tempfile, shutil
from galaxy.datatypes import data

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def check_gzip( filename ):
    temp = open( filename, "U" )
    magic_check = temp.read( 2 )
    temp.close()
    if magic_check != data.gzip_magic:
        return False
    return True

def __main__():
    filename = sys.argv[1]
    params = {}
    
    for line in open(filename, 'r'):
        try:
            line = line.strip()
            fields = line.split('\t')
            params[fields[0]] = fields[1]
        except:
            continue
    
    URL = params.get( 'URL', None )
    if not URL:
        open( filename, 'w' ).write( "" )
        #raise Exception('Datasource has not sent back a URL parameter')
        stop_err( 'Datasource has not sent back a URL parameter.' )
    out = open( filename, 'w' )
    CHUNK_SIZE = 2**20 # 1Mb 
    try:
        page = urllib.urlopen( URL, urllib.urlencode( params ) )
    except:
        stop_err( 'It appears that the UCSC Table Browser is currently offline. Please try again later.' )
    
    while 1:
        chunk = page.read( CHUNK_SIZE )
        if not chunk:
            break
        out.write( chunk )
    out.close()
    if check_gzip( filename ):
        
        gzipped_file = gzip.GzipFile( filename )
        try:
            content = gzipped_file.read()
        except IOError:
            gzipped_file.close()
            stop_err( 'Problem decompressing gzipped data.' )
        gzipped_file.close()
        
        fd, uncompressed = tempfile.mkstemp()
        os.write( fd, content ) 
        os.close( fd )
        # Replace the gzipped file with the decompressed file
        shutil.move( uncompressed, filename )        
    
if __name__ == "__main__": __main__()
