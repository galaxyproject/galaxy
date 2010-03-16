#!/usr/bin/env python

from __future__ import division

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.arrays.array_tree import *
from bx.arrays.bed import BedReader

BLOCK_SIZE = 1000

def main():
   
    input_fname = sys.argv[1]
    out_fname = sys.argv[2]
    
    reader = BedReader( open( input_fname ) )
    
    # Fill array from reader
    d = array_tree_dict_from_reader( reader, {}, block_size = BLOCK_SIZE )
    
    for array_tree in d.itervalues():
        array_tree.root.build_summary()
    
    FileArrayTreeDict.dict_to_file( d, open( out_fname, "w" ), no_leaves=True )

if __name__ == "__main__": 
    main()