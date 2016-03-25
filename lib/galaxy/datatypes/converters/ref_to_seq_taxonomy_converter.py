#!/usr/bin/env python
"""
convert a ref.taxonommy file to a seq.taxonomy file
Usage:
%python ref_to_seq_taxonomy_converter.py <ref.taxonommy_filename> <seq.taxonomy_filename> 
"""

import sys, os, re
from math import *

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( "%s" % msg )
    sys.exit()

def __main__():
    infile_name = sys.argv[1]
    outfile = open( sys.argv[2], 'w' )
    pat = '^([^ \t\n\r\x0c\x0b;]+([(]\\d+[)])?(;[^ \t\n\r\x0c\x0b;]+([(]\\d+[)]))*(;)?)$'
    for i, line in enumerate( file( infile_name ) ):
        line = line.rstrip() # eliminate trailing space and new line characters
        if not line or line.startswith( '#' ):
            continue
        fields = line.split('\t')
        # make sure the 2nd field (taxonomy) ends with a ;
        outfile.write('%s\t%s;\n' % (fields[0], re.sub(';$','',fields[1])))

    outfile.close()

if __name__ == "__main__": __main__() 