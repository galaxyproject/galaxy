#!/usr/bin/env python
#Retreives data from BIOMART and stores in a file. Biomart parameters are provided in the input/output file.
#guruprasad Ananda

import urllib, sys, os, gzip, tempfile, shutil
from galaxy import eggs

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

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
        stop_err( 'Datasource has not sent back a URL parameter.' )
    URL = URL + '&_export=1&GALAXY_URL=0'
    CHUNK_SIZE = 2**20 # 1Mb 
    MAX_SIZE   = CHUNK_SIZE * 100
    try:
        page = urllib.urlopen(URL)
    except Exception, exc:
        stop_err('Problems connecting to %s (%s)' % (URL, exc) )
    
    fp = open(filename, 'w')
    size = 0
    max_size_exceeded = False
    while 1:
        chunk = page.read(CHUNK_SIZE)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_SIZE:
            max_size_exceeded = True
            break
        fp.write(chunk)
    fp.close()
    
    if max_size_exceeded:
        print 'Maximum data size of 100 MB exceeded, incomplete data retrieval.'
    
if __name__ == "__main__": 
    __main__()
