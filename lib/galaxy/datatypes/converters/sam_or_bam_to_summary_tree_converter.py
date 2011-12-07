#!/usr/bin/env python

from __future__ import division

import sys, os, optparse
sys.stderr = open(os.devnull, 'w')  # suppress stderr as cython produces warning on some systems:
                                    # csamtools.so:6: RuntimeWarning: __builtin__.file size changed

from galaxy import eggs
import pkg_resources

if sys.version_info[:2] == (2, 4):
    pkg_resources.require( "ctypes" )
pkg_resources.require( "pysam" )

from pysam import csamtools
from galaxy.visualization.tracks.summary import *

def main():
    parser = optparse.OptionParser()
    parser.add_option( '-S', '--sam', action="store_true", dest="is_sam" )
    parser.add_option( '-B', '--bam', action="store_true", dest="is_bam" )
    options, args = parser.parse_args()
    
    if options.is_bam:
        input_fname = args[0]
        index_fname = args[1]
        out_fname = args[2]
        samfile = csamtools.Samfile( filename=input_fname, mode='rb', index_filename=index_fname )
    elif options.is_sam:
        input_fname = args[0]
        out_fname = args[1]
        samfile = csamtools.Samfile( filename=input_fname, mode='r' )
    
    st = SummaryTree(block_size=25, levels=6, draw_cutoff=150, detail_cutoff=30)
    for read in samfile.fetch():
        st.insert_range( samfile.getrname( read.rname ), read.pos, read.pos + read.rlen )
    
    st.write(out_fname)

if __name__ == "__main__": 
    main()
