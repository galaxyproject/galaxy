#!/usr/bin/env python
"""
Join two sets of intervals using their overlap as the key.

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
    -m, --mincols=N: Require this much overlap (default 1bp)
    -f, --fill=N: none, right, left, both
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.join import *
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    mincols = 1
    upstream_pad = 0
    downstream_pad = 0
    leftfill = False
    rightfill = False
    
    options, args = doc_optparse.parse( __doc__ )
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
        doc_optparse.exception()

    g1 = NiceReaderWrapper( fileinput.FileInput( in_fname ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col=strand_col_1,
                            fix_strand=True )
    g2 = NiceReaderWrapper( fileinput.FileInput( in2_fname ),
                            chrom_col=chr_col_2,
                            start_col=start_col_2,
                            end_col=end_col_2,
                            strand_col=strand_col_2,
                            fix_strand=True )

    out_file = open( out_fname, "w" )

    try:
        for outfields in join(g1, g2, mincols=mincols, rightfill=rightfill, leftfill=leftfill):
            if type( outfields ) is list:
                out_file.write( "%s\n" % "\t".join( outfields ) )
            else:
                out_file.write( "%s\n" % outfields )
    except ParseError, exc:
        out_file.close()
        fail( "Invalid file format: %s" % str( exc ) )
    except MemoryError:
        out_file.close()
        fail( "Input datasets were too large to complete the join operation." )

    out_file.close()

    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )
    if g2.skipped > 0:
        print skipped( g2, filedesc=" of 2nd dataset" )

if __name__ == "__main__":
    main()
