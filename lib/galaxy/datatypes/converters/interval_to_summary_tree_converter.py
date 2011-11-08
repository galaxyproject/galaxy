#!/usr/bin/env python

"""
Convert from interval file to summary tree file. Default input file format is BED (0-based, half-open intervals).

usage: %prog in_file out_file
    -G, --gff: input is GFF format, meaning start and end coordinates are 1-based, closed interval
"""
from __future__ import division

import sys, fileinput
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from galaxy.visualization.tracks.summary import *
from bx.intervals.io import *
from bx.cookbook import doc_optparse
from galaxy.datatypes.util.gff_util import *

def main():
    # Read options, args.
    options, args = doc_optparse.parse( __doc__ )
    try:
        gff_format = bool( options.gff )
        input_fname, out_fname = args
    except:
        doc_optparse.exception()
        
    # Do conversion.
    # TODO: take column numbers from command line.
    if gff_format:
        reader_wrapper_class = GFFReaderWrapper
        chr_col, start_col, end_col, strand_col = ( 0, 3, 4, 6 )
    else:
        reader_wrapper_class = NiceReaderWrapper
        chr_col, start_col, end_col, strand_col = ( 0, 1, 2, 5 )
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
    
    st.write(out_fname)

if __name__ == "__main__": 
    main()
