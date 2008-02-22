"""
Utility functions for galaxyops
"""

from bx.bitset import *
from bx.intervals.io import *

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

def default_printer( stream, exc, obj ):
    print >> stream, "%d: %s" % ( obj.linenum, obj.current_line )
    print >> stream, "\tError: %s" % ( str(exc) )

def skipped( reader, filedesc="" ):
    first_line, line_contents = reader.skipped_lines[0]
    return 'Data issue: skipped %d invalid lines%s starting at line #%d which is "%s"' \
           % ( reader.skipped, filedesc, first_line, line_contents )
