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
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.concat import *
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    sameformat=False
    upstream_pad = 0
    downstream_pad = 0

    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )
        if options.sameformat: sameformat = True
        in_file_1, in_file_2, out_fname = args
    except:
        doc_optparse.exception()

    g1 = NiceReaderWrapper( fileinput.FileInput( in_file_1 ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col=strand_col_1,
                            fix_strand=True )

    g2 = NiceReaderWrapper( fileinput.FileInput( in_file_2 ),
                            chrom_col=chr_col_2,
                            start_col=start_col_2,
                            end_col=end_col_2,
                            strand_col=strand_col_2,
                            fix_strand=True )

    out_file = open( out_fname, "w" )

    try:
        for line in concat( [g1, g2], sameformat=sameformat ):
            if type( line ) is GenomicInterval:
                out_file.write( "%s\n" % "\t".join( line.fields ) )
            else:
                out_file.write( "%s\n" % line )
    except ParseError, exc:
        out_file.close()
        fail( "Invalid file format: %s" % str( exc ) )

    out_file.close()

    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )
    if g2.skipped > 0:
        print skipped( g2, filedesc=" of 2nd dataset" )
        
if __name__ == "__main__":
    main()
