#!/usr/bin/env python

from __future__ import division

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "pysam" )

from pysam import csamtools
from galaxy.visualization.tracks.summary import *

def main():
   
    input_fname = sys.argv[1]
    index_fname = sys.argv[2]
    out_fname = sys.argv[3]
    
    bamfile = csamtools.Samfile( filename=input_fname, mode='rb', index_filename=index_fname )
    
    st = SummaryTree(block_size=100, levels=4, draw_cutoff=100, detail_cutoff=20)
    for read in bamfile.fetch():
        st.insert_range(bamfile.getrname(read.rname), read.pos, read.pos + read.rlen)
    
    st.write(out_fname)

if __name__ == "__main__": 
    main()