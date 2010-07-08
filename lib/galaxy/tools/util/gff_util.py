"""
Provides utilities for working with GFF files.
"""

from bx.intervals.io import NiceReaderWrapper, GenomicInterval

class GFFReaderWrapper( NiceReaderWrapper ):
    """
    Reader wrapper converts GFF format--starting and ending coordinates are 1-based, closed--to the 'traditional' interval format--0 based, 
    half-open. This is useful when using GFF files as inputs to tools that expect traditional interval format.
    """
    def parse_row( self, line ):
        interval = GenomicInterval( self, line.split( "\t" ), self.chrom_col, self.start_col, self.end_col, self.strand_col, self.default_strand, fix_strand=self.fix_strand )
        # Change from 1-based to 0-based format.
        interval.start -= 1
        # Add 1 to end to move from closed to open format for end coordinate.
        interval.end += 1
        return interval
        
def convert_to_gff_coordinates( interval ):
    """
    Converts a GenomicInterval's coordinates to GFF format.
    """
    if type( interval ) is GenomicInterval:
        interval.start += 1
        interval.end -= 1
        return interval
    return interval
