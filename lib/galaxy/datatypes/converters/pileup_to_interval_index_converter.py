#!/usr/bin/env python

"""
Convert from pileup file to interval index file.

usage: %prog <options> in_file out_file
"""

from __future__ import division

import sys, fileinput, optparse
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from galaxy.visualization.tracks.summary import *
from galaxy.datatypes.util.gff_util import convert_gff_coords_to_bed
from bx.interval_index_file import Indexes

def main():
    
    # Read options, args.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    input_fname, output_fname = args
    
    # Do conversion.
    index = Indexes()
    offset = 0
    for line in open( input_fname, "r" ):
        chrom, start = line.split()[ 0:2 ]
        # Pileup format is 1-based.
        start = int( start ) - 1
        index.add( chrom, start, start + 1, offset )
        offset += len( line )
            
    index.write( open(output_fname, "w") )

if __name__ == "__main__": 
    main()
    