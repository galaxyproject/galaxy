"""
Utility functions for galaxyops
"""

from bx.bitset import *

import sys

def warn( msg ):
    print >> sys.stderr, msg
    
def fail( msg ):
    print >> sys.stderr, msg
    sys.exit( 1 )

# Default chrom, start, end, stran cols for a bed file
BED_DEFAULT_COLS = 0, 1, 2, 5

def parse_cols_arg( cols ):
    """Parse a columns command line argument into a four-tuple"""
    if cols:
        return map( lambda x: int( x ) - 1, cols.split(",") )
    else:
        return BED_DEFAULT_COLS
