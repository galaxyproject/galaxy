#!/usr/bin/env python

"""
Convert from interval file to summary tree file. Default input file format is BED (0-based, half-open intervals).

usage: %prog <options> in_file out_file
    -c, --chr-col: chromosome column, default=1
    -s, --start-col: start column, default=2
    -e, --end-col: end column, default=3
    -t, --strand-col: strand column, default=6
    -G, --gff: input is GFF format, meaning start and end coordinates are 1-based, closed interval
"""
from __future__ import division

import sys, fileinput, optparse
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from galaxy.visualization.tracks.summary import *
from bx.intervals.io import *
from galaxy.datatypes.util.gff_util import *

def main():
    # Read options, args.
    parser = optparse.OptionParser()
    parser.add_option( '-c', '--chr-col', type='int', dest='chrom_col', default=1 )
    parser.add_option( '-s', '--start-col', type='int', dest='start_col', default=2 )
    parser.add_option( '-e', '--end-col', type='int', dest='end_col', default=3 )
    parser.add_option( '-t', '--strand-col', type='int', dest='strand_col', default=6 )
    parser.add_option( '-G', '--gff', dest="gff_format", action="store_true" )
    (options, args) = parser.parse_args()
    input_fname, output_fname = args
    
    # Convert column indices to 0-based.
    options.chrom_col -= 1
    options.start_col -= 1
    options.end_col -= 1
    options.strand_col -= 1
        
    # Do conversion.
    if options.gff_format:
        reader_wrapper_class = GFFReaderWrapper
        chr_col, start_col, end_col, strand_col = ( 0, 3, 4, 6 )
    else:
        reader_wrapper_class = NiceReaderWrapper
        chr_col, start_col, end_col, strand_col = ( options.chrom_col, options.start_col, options.end_col, options.strand_col )
    reader_wrapper = reader_wrapper_class( fileinput.FileInput( input_fname ),
                                            chrom_col=chr_col,
                                            start_col=start_col,
                                            end_col=end_col,
                                            strand_col=strand_col,
                                            fix_strand=True )
    st = SummaryTree(block_size=25, levels=6, draw_cutoff=150, detail_cutoff=30)
    for feature in list( reader_wrapper ):
        if isinstance( feature, GenomicInterval ):
            # Tree expects BED coordinates.
            if type( feature ) is GFFFeature:
                convert_gff_coords_to_bed( feature )
            st.insert_range( feature.chrom, long( feature.start ), long( feature.end ) )
    
    st.write( output_fname )

if __name__ == "__main__": 
    main()
