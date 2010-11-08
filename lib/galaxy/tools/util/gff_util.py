"""
Provides utilities for working with GFF files.
"""

from bx.intervals.io import NiceReaderWrapper, GenomicInterval

class GFFReaderWrapper( NiceReaderWrapper ):
    """
    Reader wrapper converts GFF format--starting and ending coordinates are 1-based, closed--to the 
    'traditional'/BED interval format--0 based, half-open. This is useful when using GFF files as inputs 
    to tools that expect traditional interval format.
    """
    def parse_row( self, line ):
        interval = GenomicInterval( self, line.split( "\t" ), self.chrom_col, self.start_col, self.end_col, \
                                    self.strand_col, self.default_strand, fix_strand=self.fix_strand )
        interval = convert_gff_coords_to_bed( interval )
        return interval
        
def convert_bed_coords_to_gff( interval ):
    """
    Converts an interval object's coordinates from BED format to GFF format. Accepted object types include 
    GenomicInterval and list (where the first element in the list is the interval's start, and the second 
    element is the interval's end).
    """
    if type( interval ) is GenomicInterval:
        interval.start += 1
    elif type ( interval ) is list:
        interval[ 0 ] += 1
    return interval
    
def convert_gff_coords_to_bed( interval ):
    """
    Converts an interval object's coordinates from GFF format to BED format. Accepted object types include 
    GenomicInterval and list (where the first element in the list is the interval's start, and the second 
    element is the interval's end).
    """
    if type( interval ) is GenomicInterval:
        interval.start -= 1
    elif type ( interval ) is list:
        interval[ 0 ] -= 1
    return interval
    
def parse_gff_attributes( attr_str ):
    """
    Parses a GFF/GTF attribute string and returns a dictionary of name-value pairs.
    The general format for a GFF3 attributes string is name1=value1;name2=value2
    The general format for a GTF attribute string is name1 "value1" ; name2 "value2"
    """
    attributes_list = attr_str.split(";")
    attributes = {}
    for name_value_pair in attributes_list:
        # Try splitting by space and, if necessary, by '=' sign.
        pair = name_value_pair.strip().split(" ")
        if len( pair ) == 1:
            pair = name_value_pair.strip().split("=")
        print pair
        if pair == '':
            continue
        name = pair[0].strip()
        if name == '':
            continue
        # Need to strip double quote from values
        value = pair[1].strip(" \"")
        attributes[ name ] = value
    return attributes