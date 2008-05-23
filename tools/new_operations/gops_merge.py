#!/usr/bin/env python
"""
Merge overlaping regions.

usage: %prog in_file out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -m, --mincols=N: Require this much overlap (default 1bp)
    -3, --threecol: Output 3 column bed
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.merge import *
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    mincols = 1
    upstream_pad = 0
    downstream_pad = 0

    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        if options.mincols: mincols = int( options.mincols )
        in_fname, out_fname = args
    except:
        doc_optparse.exception()

    g1 = NiceReaderWrapper( fileinput.FileInput( in_fname ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col = strand_col_1,
                            fix_strand=True )

    out_file = open( out_fname, "w" )

    try:
        for line in merge(g1,mincols=mincols):
            if options.threecol:
                if type( line ) is GenomicInterval:
                    out_file.write( "%s\t%s\t%s\n" % ( line.chrom, str( line.startCol ), str( line.endCol ) ) )
                elif type( line ) is list:
                    out_file.write( "%s\t%s\t%s\n" % ( line[chr_col_1], str( line[start_col_1] ), str( line[end_col_1] ) ) )
                else:
                    out_file.write( "%s\n" % line )
            else:
                if type( line ) is GenomicInterval:
                    out_file.write( "%s\n" % "\t".join( line.fields ) )
                elif type( line ) is list:
                    out_file.write( "%s\n" % "\t".join( line ) )
                else:
                    out_file.write( "%s\n" % line )
    except ParseError, exc:
        out_file.close()
        fail( "Invalid file format: %s" % str( exc ) )

    out_file.close()

    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )

if __name__ == "__main__":
    main()
