#!/usr/bin/env python

"""
Calculate coverage of one query on another, and append the coverage to
the last two columns as bases covered and percent coverage.

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import sys
import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.coverage import *
import cookbook.doc_optparse

from galaxyops import *

def main():

    upstream_pad = 0
    downstream_pad = 0

    options, args = cookbook.doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )      
        in_fname, in2_fname, out_fname = args
    except:
        cookbook.doc_optparse.exception()

    g1 = GenomicIntervalReader( fileinput.FileInput( in_fname ),
                                chrom_col=chr_col_1,
                                start_col=start_col_1,
                                end_col=end_col_1,
                                strand_col=strand_col_1,
                                fix_strand=True)
    g2 = GenomicIntervalReader( fileinput.FileInput( in2_fname ),
                                chrom_col=chr_col_2,
                                start_col=start_col_2,
                                end_col=end_col_2,
                                strand_col=strand_col_2,
                                fix_strand=True)
    out_file = open( out_fname, "w" )

    try:
        for line in coverage([g1,g2]):
            if type( line ) is GenomicInterval:
                print >> out_file, "\t".join( line.fields )
            else:
                print >> out_file, line
    except ParseError, exc:
        print >> sys.stderr, "Invalid file format: ", str( exc )

if __name__ == "__main__":
    main()
