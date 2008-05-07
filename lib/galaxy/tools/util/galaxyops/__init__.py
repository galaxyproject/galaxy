"""
Utility functions for galaxyops
"""
import sys

from bx.bitset import *
from bx.intervals.io import *

class BitsetSafeNiceReaderWrapper:
    """Handles exceptions thrown in bx."""
    def __init__( self, iterat ):
        self.iterat = iterat
        self.MAXINT = 2147483647 # max signed int value for 32-bit
    def __iter__( self ):
        while True:
            region = self.iterat.next()
            # NiceReaderWrapper can return a header, comment or GenomicInterval
            if type( region ) == GenomicInterval:
                if ( region.start > self.MAXINT ) or ( region.end > self.MAXINT ) or ( region.start > region.end ):
                    self.iterat.skipped += 1
                    if self.iterat.skipped < 10:
                        self.iterat.skipped_lines.append( ( self.iterat.linenum, self.iterat.current_line ) )
                else:
                    yield region
    def __getattr__( self, name ):
        return getattr( self.iterat, name )
    def binned_bitsets( self , upstream_pad=0, downstream_pad=0, lens={} ):
        # This is duplicated in bx.intervals.io, but we need it here so that self refers to 
        # our BitsetSafeNiceReaderWrapper rather than bx.intervals.io's GenomicIntervalReader
        last_chrom = None
        last_bitset = None
        bitsets = dict()
        for interval in self:
            if type( interval ) == GenomicInterval:
                chrom = interval[self.chrom_col]
                if chrom != last_chrom:
                    if chrom not in bitsets:
                        if chrom in lens:
                            size = lens[chrom]
                        else:
                            size = MAX
                        bitsets[chrom] = BinnedBitSet( size )
                    last_chrom = chrom
                    last_bitset = bitsets[chrom]
                start = max(int( interval[self.start_col]), 0 )
                end = min(int( interval[self.end_col]), size)
                last_bitset.set_range( start, end-start )
        return bitsets

def warn( msg ):
    # TODO: since everything printed to stderr results in job.state = error, we
    # don't need both a warn and a fail...
    print >> sys.stderr, msg
    sys.exit( 1 )
    
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
    return 'Skipped %d invalid lines%s starting at line #%d: "%s"' \
           % ( reader.skipped, filedesc, first_line, line_contents )
