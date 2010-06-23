#!/usr/bin/env python
"""
Find regions of first interval/GFF file that overlap regions in a second interval/GFF file

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
    -m, --mincols=N: Require this much overlap (default 1bp)
    -p, --pieces: just print pieces of second set (after padding)
    -G, --gff1: input 1 is GFF format, meaning start and end coordinates are 1-based, closed interval
    -H, --gff2: input 2 is GFF format, meaning start and end coordinates are 1-based, closed interval
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.intersect import *
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *
from galaxy.tools.util.gff_util import *

assert sys.version_info[:2] >= ( 2, 4 )

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
        in1_gff_format = bool( options.gff1 )
        in2_gff_format = bool( options.gff2 )
        in_fname, in2_fname, out_fname = args
    except:
        doc_optparse.exception()
        
    # Set readers to handle either GFF or default format.
    if in1_gff_format:
        in1_reader_wrapper = GFFReaderWrapper
    else:
        in1_reader_wrapper = NiceReaderWrapper
    if in2_gff_format:
        in2_reader_wrapper = GFFReaderWrapper
    else:
        in2_reader_wrapper = NiceReaderWrapper
        
    g1 = in1_reader_wrapper( fileinput.FileInput( in_fname ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col=strand_col_1,
                            fix_strand=True )
    g2 = in2_reader_wrapper( fileinput.FileInput( in2_fname ),
                            chrom_col=chr_col_2,
                            start_col=start_col_2,
                            end_col=end_col_2,
                            strand_col=strand_col_2,
                            fix_strand=True )

    out_file = open( out_fname, "w" )

    try:
        for line in intersect( [g1,g2], pieces=pieces, mincols=mincols ):
            if type( line ) == GenomicInterval:
                if in1_gff_format:
                    line = convert_to_gff_coordinates( line )
                out_file.write( "%s\n" % "\t".join( line.fields ) )
            else:
                out_file.write( "%s\n" % line )
    except ParseError, e:
        out_file.close()
        fail( "Invalid file format: %s" % str( e ) )

    out_file.close()

    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )
    if g2.skipped > 0:
        print skipped( g2, filedesc=" of 2nd dataset" )

if __name__ == "__main__":
    main()
