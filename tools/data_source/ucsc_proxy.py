#!/usr/bin/env python
import urllib
import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

CHUNK   = 2**20 # 1Mb 
MAXSIZE = CHUNK * 100
if __name__ == '__main__':

    if len(sys.argv) != 3:
        print 'Usage ucsc.py input_params output_file'
        sys.exit()

    inp_file = sys.argv[1]
    out_file = sys.argv[2]

    DEFAULT_URL = "http://genome.ucsc.edu/hgTables?"
    
    # this must stay a list to allow multiple selections for the same widget name (checkboxes)
    params  = []
    for line in file(inp_file):
        line = line.strip()
        if line:
            parts = line.split('=')
            if len(parts) == 0:
                key = ""
                value = ""
            elif len(parts) == 1:
                key = parts[0]
                value = ""
            else:
                key = parts[0]
                value = parts[1]
            if key == 'display':
                print value
            # get url from params, refered from proxy.py, initialized by the tool xml
            elif key == 'proxy_url':
                DEFAULT_URL = value
            else:
                params.append( (key, value) )
    
    #print params
    
    encoded_params = urllib.urlencode(params)
    url = DEFAULT_URL + encoded_params

    #print url

    page = urllib.urlopen(url)

    fp = open(out_file, 'wt')
    size = 0
    while 1:
        data = page.read(CHUNK)
        if not data:
            break
        if size > MAXSIZE:
            fp.write('----- maximum datasize exceeded ---\n')
            break
        size += len(data)
        fp.write(data)

    fp.close()

