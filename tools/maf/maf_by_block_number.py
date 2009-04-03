#!/usr/bin/env python
#Dan Blankenberg
"""
Reads a list of block numbers and a maf. Produces a new maf containing the
blocks specified by number.
"""

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from galaxy.tools.util import maf_utilities
import bx.align.maf

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
    input_block_filename = sys.argv[1].strip()
    input_maf_filename = sys.argv[2].strip()
    output_filename1 = sys.argv[3].strip()
    block_col = int( sys.argv[4].strip() ) - 1
    if block_col < 0:
        print >> sys.stderr, "Invalid column specified"
        sys.exit(0)
    species = maf_utilities.parse_species_option( sys.argv[5].strip() )
    
    maf_writer = bx.align.maf.Writer( open( output_filename1, 'w' ) )
    #we want to maintain order of block file and write blocks as many times as they are listed
    failed_lines = []
    for ctr, line in enumerate( open( input_block_filename, 'r' ) ):
        try:
            block_wanted = int( line.split( "\t" )[block_col].strip() )
        except:
            failed_lines.append( str( ctr ) )
            continue
        try:
            for count, block in enumerate( bx.align.maf.Reader( open( input_maf_filename, 'r' ) ) ):
                if count == block_wanted:
                    if species:
                        block = block.limit_to_species( species )
                    maf_writer.write( block )
                    break
        except:
            print >>sys.stderr, "Your MAF file appears to be malformed."
            sys.exit()
    if len( failed_lines ) > 0: print "Failed to extract from %i lines (%s)." % ( len( failed_lines ), ",".join( failed_lines ) )
if __name__ == "__main__": __main__()
