#!/usr/bin/env python

from __future__ import division

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.interval_index_file import Indexes

def main():
    
    input_fname = sys.argv[1]
    out_fname = sys.argv[2]
    index = Indexes()
    offset = 0
    
    for line in open(input_fname, "r"):
        feature = line.split()
        if not feature or feature[0] == "track" or feature[0] == "#":
            offset += len(line)
            continue
        chrom = feature[0]
        chrom_start = int(feature[1])
        chrom_end = int(feature[2])
        index.add( chrom, chrom_start, chrom_end, offset )
        offset += len(line)
    
    index.write( open(out_fname, "w") )

if __name__ == "__main__": 
    main()
    