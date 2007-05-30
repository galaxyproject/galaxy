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

class NiceReaderWrapper( GenomicIntervalReader ):
    def __init__( self, reader, **kwargs ):
        GenomicIntervalReader.__init__( self, reader, **kwargs )
        self.outstream = kwargs.get("outstream", None)
        self.print_delegate = kwargs.get("print_delegate", None)
        self.skipped = 0
        self.skipped_lines = []
        self.input_wrapper = iter( self.input )
        self.input_iter = self.iterwrapper()
    def __iter__( self ):
        return self
    def next( self ):
        while 1:
            try:
                nextitem = GenomicIntervalReader.next( self )
                return nextitem
            except ParseError, e:
                if self.outstream:
                    if self.print_delegate and hasattr(self.print_delegate,"__call__"):
                        self.print_delegate( self.outstream, e, self )
                self.skipped += 1
                # no reason to stuff an entire bad file into memmory
                if self.skipped < 10:
                    self.skipped_lines.append( (self.linenum, self.current_line) )
    def iterwrapper( self ):
        while 1:
            self.current_line = self.input_wrapper.next()
            yield self.current_line

def default_printer( stream, exc, obj ):
    print >> stream, "%d: %s" % ( obj.linenum, obj.current_line )
    print >> stream, "\tError: %s" % ( str(exc) )

def skipped( reader, filedesc="" ):
    first_line, line_contents = reader.skipped_lines[0]
    return 'Data issue: skipped %d invalid lines%s starting at line #%d which is "%s"' \
           % ( reader.skipped, filedesc, first_line, line_contents )
