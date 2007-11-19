#Adapted from bx/intervals/operations/coverage.py
"""
Determine amount of each interval in one set covered by the intervals of 
another set. Adds two columns to the first input, giving number of bases 
covered and percent coverage on the second input.
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import psyco_full

import traceback
import fileinput
from warnings import warn

from bx.intervals.io import *
from bx.intervals.operations import *

def coverage(readers, comments=True):
    # Read all but first into bitsets and union to one
    primary = readers[0]
    intersect = readers[1:]
    bitsets = intersect[0].binned_bitsets()
    intersect = intersect[1:]
    for andset in intersect:
        bitset2 = andset.binned_bitsets()
        for chrom in bitsets:
            if chrom not in bitset2: continue
            bitsets[chrom].ior(bitset2[chrom])
        intersect = intersect[1:]

    # Read remaining intervals and give coverage
    for interval in primary:
        if type( interval ) is Header:
            yield interval
        if type( interval ) is Comment and comments:
            yield interval
        elif type( interval ) == GenomicInterval:
            chrom = interval.chrom
            start = int(interval.start)
            end = int(interval.end)
            if start > end: warn( "Interval start after end!" )
            if chrom not in bitsets:
                bases_covered = 0
                percent = 0.0
            else:
                bases_covered = bitsets[ chrom ].count_range( start, end-start )
                if (end - start) == 0: percent = 0
                else: percent = float(bases_covered) / float(end - start)
            interval.fields.append(str(bases_covered))
            interval.fields.append(str(percent))
            yield interval
