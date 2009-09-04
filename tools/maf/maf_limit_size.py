#!/usr/bin/env python
#Dan Blankenberg
"""
Removes blocks that fall outside of specified size range.
"""

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():

    input_maf_filename = sys.argv[1].strip()
    output_filename1 = sys.argv[2].strip()
    min_size = int( sys.argv[3].strip() )
    max_size = int( sys.argv[4].strip() )
    if max_size < 1: max_size = sys.maxint
    maf_writer = bx.align.maf.Writer( open( output_filename1, 'w' ) )
    try:
        maf_reader = bx.align.maf.Reader( open( input_maf_filename, 'r' ) )
    except:
        print >>sys.stderr, "Your MAF file appears to be malformed."
        sys.exit()
    
    blocks_kept = 0
    i = 0
    for i, m in enumerate( maf_reader ):
        if min_size <= m.text_size <= max_size:
            maf_writer.write( m )
            blocks_kept += 1
    print 'Kept %s of %s blocks (%.2f%%).' % ( blocks_kept, i + 1, float( blocks_kept ) / float( i + 1 ) * 100.0 )

if __name__ == "__main__": __main__()
