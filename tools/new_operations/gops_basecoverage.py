#!/usr/bin/env python
"""
Count total base coverage.

usage: %prog in_file out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.base_coverage import *
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    upstream_pad = 0
    downstream_pad = 0

    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        in_fname, out_fname = args
    except:
        doc_optparse.exception()
        
    g1 = NiceReaderWrapper( fileinput.FileInput( in_fname ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col = strand_col_1,
                            fix_strand=True )
    
    try:
        bases = base_coverage(g1)
    except ParseError, exc:
        fail( "Invalid file format: %s" % str( exc ) )
    out_file = open( out_fname, "w" )
    out_file.write( "%s\n" % str( bases ) )
    out_file.close()
    if g1.skipped > 0:
        print skipped( g1, filedesc="" )

if __name__ == "__main__":
    main()
