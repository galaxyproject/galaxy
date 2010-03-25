#!/usr/bin/env python

from __future__ import division

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from galaxy.visualization.tracks.summary import *
from bx.arrays.bed import BedReader

def main():
   
    input_fname = sys.argv[1]
    out_fname = sys.argv[2]
    
    reader = BedReader( open( input_fname ) )
    
    st = SummaryTree(block_size=100, levels=4, draw_cutoff=100, detail_cutoff=20)
    for chrom, chrom_start, chrom_end, name, score in reader:
        st.insert_range(chrom, chrom_start, chrom_end)
    
    st.write(out_fname)    

if __name__ == "__main__": 
    main()