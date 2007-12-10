#!/usr/bin/env python2.4
#Retreives data from UCSC and stores in a file. UCSC parameters are provided in the input/output file.
import urllib, sys
import StringIO, gzip

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
    
    URL = params.get('URL',None)
    if not URL:
        open(filename, 'w').write("")
        #raise Exception('Datasource has not sent back a URL parameter')
        print >> sys.stderr, 'Datasource has not sent back a URL parameter'
        sys.exit(0)
    
    out = open(filename, 'w')
    
    CHUNK_SIZE = 2**20 # 1Mb 
    try:
        page = urllib.urlopen(URL, urllib.urlencode(params))
    except Exception, exc:
        #raise Exception('Problems connecting to %s (%s)' % (URL, exc) )
        #print >> sys.stderr, 'Problems connecting to %s (%s)' % (URL, exc)
        print >> sys.stderr, 'It appears that the UCSC Table Browser is currently offline. You may try again later.'
        sys.exit(0)

    gzipped = False
    first_chunk = True
    
    while 1:
        chunk = page.read( CHUNK_SIZE )
        if not chunk:
            break
        if first_chunk:
            first_chunk = False
            # The magic number of a gzipped file is comprised of the first 2 characters of the file
            if chunk[0:2] == '\037\213':
                gzipped = True
        if gzipped:
            compressed_stream = StringIO.StringIO( chunk )   
            gzipper = gzip.GzipFile( fileobj=compressed_stream )      
            chunk = gzipper.read()   
        out.write( chunk )
    out.close()
    
if __name__ == "__main__": __main__()
