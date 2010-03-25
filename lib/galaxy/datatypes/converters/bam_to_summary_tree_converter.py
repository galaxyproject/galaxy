#!/usr/bin/env python

from __future__ import division

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" ); pkg_resources.require( "pysam" )

from pysam import csamtools
from bx.arrays.array_tree import *

BLOCK_SIZE = 1000

class BamReader:
    def __init__( self, input_fname, index_fname ):
        self.bamfile = csamtools.Samfile( filename=input_fname, mode='rb', index_filename=index_fname )
        self.iterator = self.bamfile.fetch()
    
    def __iter__( self ):
        return self
    
    def __next__( self ):
        while True:
            read = self.iterator.next()
            return read.rname, read.mpos, read.pos + read.rlen, None, mapq
    

def main():
   
    input_fname = sys.argv[1]
    index_fname = sys.argv[2]
    out_fname = sys.argv[3]
    
    reader = BamReader( input_fname, index_fname )
    
    # Fill array from reader
    d = array_tree_dict_from_reader( reader, {}, block_size = BLOCK_SIZE )
    
    for array_tree in d.itervalues():
        array_tree.root.build_summary()
    
    FileArrayTreeDict.dict_to_file( d, open( out_fname, "w" ), no_leaves=True )

if __name__ == "__main__": 
    main()