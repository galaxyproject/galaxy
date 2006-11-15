#!/usr/bin/env python

"""
Join two sets of intervals using their overlap as the key.

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
    -m, --mincols=N: Require this much overlap (default 1bp)
    -f, --fill=N: none, right, left, both
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.join import *
import cookbook.doc_optparse

from galaxyops import *

def main():

    mincols = 1
    upstream_pad = 0
    downstream_pad = 0
    leftfill = False
    rightfill = False
    
    options, args = cookbook.doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )      
        if options.mincols: mincols = int( options.mincols )
        if options.fill:
            if options.fill == "both":
                rightfill = leftfill = True
            else:
                rightfill = options.fill == "right"
                leftfill = options.fill == "left"
        in_fname, in2_fname, out_fname = args
    except:
        cookbook.doc_optparse.exception()

    g1 = GenomicIntervalReader( fileinput.FileInput( in_fname ),
                                chrom_col=chr_col_1,
                                start_col=start_col_1,
                                end_col=end_col_1,
                                strand_col=strand_col_1)
    g2 = GenomicIntervalReader( fileinput.FileInput( in2_fname ),
                                chrom_col=chr_col_2,
                                start_col=start_col_2,
                                end_col=end_col_2,
                                strand_col=strand_col_2)
    out_file = open( out_fname, "w" )


    for outfields in join(g1, g2, mincols=mincols, rightfill=rightfill, leftfill=leftfill):
        if type( outfields ) is list:
            print >> out_file, "\t".join(outfields)
        else:
            print >> out_file, outfields

if __name__ == "__main__":
    main()
