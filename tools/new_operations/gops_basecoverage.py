#!/usr/bin/env python

"""
Count total base coverage.

usage: %prog in_file out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import sys
import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.base_coverage import *
import cookbook.doc_optparse

from galaxyops import *

def main():

    upstream_pad = 0
    downstream_pad = 0

    options, args = cookbook.doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        in_fname, out_fname = args
    except:
        cookbook.doc_optparse.exception()

    g1 = GenomicIntervalReader( fileinput.FileInput( in_fname ),
                                chrom_col=chr_col_1,
                                start_col=start_col_1,
                                end_col=end_col_1)
    if strand_col_1 >= 0:
        g1.strand_col=strand_col_1

    out_file = open( out_fname, "w" )

    bases = base_coverage(g1)
    print >> out_file, str(bases)

if __name__ == "__main__":
    main()
