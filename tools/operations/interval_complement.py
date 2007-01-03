#!/usr/bin/env python

"""
Complement the regions of a bed file. Requires a file that maps source names
to sizes. This should be in the simple LEN file format (each line contains
source build, a source name(chr), followed by a size, separated by whitespace).
The file: /cache/chrominfo.txt appears to be acceptable

usage: %prog len_fname build in_fname out_fname chrom_col start_col end_col strand_col
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import sys

from bx.bitset import *
from bx.bitset_builders import *

import cookbook.doc_optparse

def read_len( f, build ):
    """Read a 'LEN' file and return a mapping from chromosome to length"""
    mapping = dict()
    for line in f:
        fields = line.split()
        if fields[0] == build:
            mapping[ fields[1] ] = int( fields[2] )
    return mapping




options, args = cookbook.doc_optparse.parse( __doc__ )
try:
    len_fname, build, in_fname, out_fname, chrom_col, start_col, end_col, strand_col = args
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
    #cookbook.doc_optparse.exit()

try:
    bitsets = binned_bitsets_from_file( open( in_fname ), chrom_col=chrom_col, start_col=start_col, end_col=end_col, strand_col=strand_col )
except:
    print >> sys.stderr, "Unable to Load Input file."
    sys.exit(0)

try:
    lens = read_len( open( len_fname ), build )
except:
    print >> sys.stderr, "Unable to Load chromosome information."
    sys.exit(0)

try:
    out_file = open(out_fname, "w")
except:
    print >> sys.stderr, "Unable to open output file"
    sys.exit(0)

for chrom in lens:
    if chrom in bitsets:
        bits = bitsets[chrom]
        bits.invert()
        len = lens[chrom]
        end = 0
        while 1:
            start = bits.next_set( end )
            if start == bits.size: break
            end = bits.next_clear( start )
            if end > len: end = len
            print >>out_file, "%s\t%d\t%d" % ( chrom, start, end )
            if end == len: break
    else:
        print >>out_file, "%s\t%d\t%d" % ( chrom, 0, lens[chrom] )
