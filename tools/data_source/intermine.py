#!/usr/bin/env python
#Retreives data from intermine and stores in a file. Intermine parameters are provided in the input/output file.
import urllib, sys, os, gzip, tempfile, shutil
from galaxy import eggs
from galaxy.datatypes import data

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

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
        stop_err( 'Datasource has not sent back a URL parameter.' )

    CHUNK_SIZE = 2**20 # 1Mb 
    try:
        page = urllib.urlopen( URL )
    except Exception, exc:
        raise Exception( 'Problems connecting to %s (%s)' % ( URL, exc ) )
        sys.exit( 1 )
    
    fp = open( filename, 'wb' )
    while 1:
        chunk = page.read( CHUNK_SIZE )
        if not chunk:
            break
        fp.write( chunk )
    fp.close()     
    
if __name__ == "__main__": __main__()
