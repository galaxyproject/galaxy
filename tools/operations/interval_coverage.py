#!/usr/bin/env python

"""
Print number of bases covered by intervals in an interval file. 

usage: %prog in_fname out_fname chrom_col start_col end_col strand_col
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import psyco_full
import sys
from bx.bitset import BinnedBitSet
from bx.bitset_builders import *
from itertools import *
import cookbook.doc_optparse

options, args = cookbook.doc_optparse.parse( __doc__ )
try:
    in_fname, out_fname, chrom_col, start_col, end_col, strand_col = args
    chrom_col=int(chrom_col)-1
    start_col=int(start_col)-1
    end_col=int(end_col)-1
    #if no strand, trick binned_bitsets to make always +
    if int(strand_col) <= 0:
        strand_col=sys.maxint
    else:
        strand_col=int(strand_col)-1
except:
    print >> sys.stderr, "Invalid Arguments"
    sys.exit(0)

try:
    out_file = open(out_fname, "w")
except:
    print >> sys.stderr, "Unable to open output file"
    sys.exit(0)

try:
    bitsets = binned_bitsets_from_file( open( in_fname ), chrom_col=chrom_col, start_col=start_col, end_col=end_col, strand_col=strand_col )
except:
    print >> sys.stderr, "Unable to Load Input file."
    sys.exit(0)

total = 0
for chrom in bitsets:
    total += bitsets[chrom].count_range( 0, bitsets[chrom].size )

print >> out_file, total

out_file.close()