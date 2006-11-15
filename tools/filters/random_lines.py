#!/usr/bin/env python

"""
Sample some number of random lines from a file. Needs to passes over the 
input (but that saves us memory).

usage: %prog in_fname out_fname nlines
"""

import random, sys

in_fname, out_fname, lines = sys.argv[1:]
lines = int( lines )

# First pass, count lines in input
nlines = 0
for line in open( in_fname ):
    nlines += 1
    
# Sample
sample = random.sample( range( nlines ), nlines )
 
# Second pass, select sampled lines and print
out = open( out_fname, 'w' )
for i, line in enumerate( open( in_fname ) ):
    if i in sample:
        print >> out, line,
out.close()