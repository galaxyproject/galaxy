#!/usr/bin/env python

"""
Find regions of first bed file that overlap regions in a second bed file

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
    -m, --mincols=N: Require this much overlap (default 1bp)
    -p, --pieces: just print pieces of second set (after padding)
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import sys
import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.intersect import *
from bx.cookbook import doc_optparse

from galaxyops import *

def main():

    mincols = 1
    upstream_pad = 0
    downstream_pad = 0

    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )      
        if options.mincols: mincols = int( options.mincols )
        pieces = bool( options.pieces )
        in_fname, in2_fname, out_fname = args
    except:
        doc_optparse.exception()

    g1 = NiceReaderWrapper( fileinput.FileInput( in_fname ),
                                chrom_col=chr_col_1,
                                start_col=start_col_1,
                                end_col=end_col_1,
                                strand_col=strand_col_1,
                                fix_strand=True)
    g2 = NiceReaderWrapper( fileinput.FileInput( in2_fname ),
                                chrom_col=chr_col_2,
                                start_col=start_col_2,
                                end_col=end_col_2,
                                strand_col=strand_col_2,
                                fix_strand=True)

    out_file = open( out_fname, "w" )

    try:
        for line in intersect([g1,g2], pieces=pieces, mincols=mincols):
            if type( line ) is GenomicInterval:
                print >> out_file, "\t".join( line.fields )
            else:
                print >> out_file, line
    except ParseError, exc:
        print >> sys.stderr, "Invalid file format: ", str( exc )

    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )

    if g2.skipped > 0:
        print skipped( g2, filedesc=" of 2nd dataset" )

if __name__ == "__main__":
    main()
