#!/usr/bin/env python

"""
Concatenate two bed files.  The concatenated files are returned in the
same format as the first.  If --sameformat is specified, then all
columns will be treated as the same, and all fields will be saved,
although the output will be trimmed to match the primary input.  In
addition, if --sameformat is specified, missing fields will be padded
with a period(.).

usage: %prog in_file_1 in_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for chrom, start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for chrom, start, end, strand in second file
    -s, --sameformat: All files are precisely the same format.
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import sys
import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.concat import *
import cookbook.doc_optparse

from galaxyops import *

def main():

    sameformat=False
    upstream_pad = 0
    downstream_pad = 0

    options, args = cookbook.doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )
        if options.sameformat: sameformat = True
        in_file_1, in_file_2, out_fname = args
    except:
        cookbook.doc_optparse.exception()

    g1 = GenomicIntervalReader( fileinput.FileInput( in_file_1 ),
                                chrom_col=chr_col_1,
                                start_col=start_col_1,
                                end_col=end_col_1)
    if strand_col_1 >= 0:
        g1.strand_col=strand_col_1
        
    g2 = GenomicIntervalReader( fileinput.FileInput( in_file_2 ),
                                chrom_col=chr_col_2,
                                start_col=start_col_2,
                                end_col=end_col_2,
                                strand_col=strand_col_2)
    
    out_file = open( out_fname, "w" )

    for line in concat([g1, g2], sameformat=sameformat):
        if type( line ) is GenomicInterval:
            print >> out_file, "\t".join( line.fields )
        else:
            print >> out_file, line

if __name__ == "__main__":
    main()
