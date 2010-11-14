#!/usr/bin/env python

"""
Convert from interval file to interval index file. Default input file format is BED (0-based, half-open intervals).

usage: %prog in_file out_file
    -G, --gff: input is GFF format, meaning start and end coordinates are 1-based, closed interval
"""

from __future__ import division

import sys, fileinput
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from galaxy.visualization.tracks.summary import *
from bx.cookbook import doc_optparse
from galaxy.datatypes.util.gff_util import convert_gff_coords_to_bed
from bx.interval_index_file import Indexes

def main():
    
    # Read options, args.
    options, args = doc_optparse.parse( __doc__ )
    try:
        gff_format = bool( options.gff )
        input_fname, out_fname = args
    except:
        doc_optparse.exception()
    
    # Do conversion.
    # TODO: take column numbers from command line.
    if gff_format:
        chr_col, start_col, end_col = ( 0, 3, 4 )
    else:
        chr_col, start_col, end_col = ( 0, 1, 2 )
    index = Indexes()
    offset = 0
    for line in open(input_fname, "r"):
        feature = line.strip().split()
        if not feature or feature[0].startswith("track") or feature[0].startswith("#"):
            offset += len(line)
            continue
        chrom = feature[ chr_col ]
        chrom_start = int( feature[ start_col ] )
        chrom_end = int( feature[ end_col ] )
        if gff_format:
            chrom_start, chrom_end = convert_gff_coords_to_bed( [chrom_start, chrom_end ] )
        index.add( chrom, chrom_start, chrom_end, offset )
        offset += len(line)
            
    index.write( open(out_fname, "w") )

if __name__ == "__main__": 
    main()
    