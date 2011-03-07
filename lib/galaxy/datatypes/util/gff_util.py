"""
Provides utilities for working with GFF files.
"""
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.intervals.io import *
from bx.tabular.io import Header, Comment

class GFFInterval( GenomicInterval ):
    """ 
    A GFF interval, including attributes. If file is strictly a GFF file,
    only attribute is 'group.'
    """
    def __init__( self, reader, fields, chrom_col, start_col, end_col, strand_col, \
                  score_col, default_strand, fix_strand=False, raw_line='' ):
        GenomicInterval.__init__( self, reader, fields, chrom_col, start_col, end_col, strand_col, \
                                  default_strand, fix_strand=fix_strand )
        # Handle score column.
        self.score_col = score_col
        if self.score_col >= self.nfields:
          raise MissingFieldError( "No field for score_col (%d)" % score_col )
        self.score = self.fields[ self.score_col ]
        
        # Attributes specific to GFF.
        self.raw_line = raw_line
        self.attributes = parse_gff_attributes( fields[8] )
                
class GFFFeature( GFFInterval ):
    """
    A GFF feature, which can include multiple intervals.
    """
    def __init__( self, reader, chrom_col, start_col, end_col, strand_col, score_col, default_strand, \
                  fix_strand=False, intervals=[] ):
        GFFInterval.__init__( self, reader, intervals[0].fields, chrom_col, start_col, end_col, \
                                strand_col, score_col, default_strand, fix_strand=fix_strand )
        self.intervals = intervals
        # Use intervals to set feature attributes.
        for interval in self.intervals:
            # Error checking.
            if interval.chrom != self.chrom:
                raise ValueError( "interval chrom does not match self chrom: %i != %i" % \
                                  ( interval.chrom, self.chrom ) )
            if interval.strand != self.strand:
                raise ValueError( "interval strand does not match self strand: %s != %s" % \
                                  ( interval.strand, self.strand ) )
            # Set start, end of interval.
            if interval.start < self.start:
                self.start = interval.start
            if interval.end > self.end:
                self.end = interval.end
                
    def name( self ):
        """ Returns feature's name. """
        name = self.attributes.get( 'transcript_id', None )
        if not name:
            name = self.attributes.get( 'id', None )
        if not name:
            name = self.attributes.get( 'group', None )
        return name
        
    def raw_size( self ):
        """
        Returns raw size of feature; raw size is the number of bytes that
        comprise feature.
        """
        # Feature length is all intervals/lines that comprise feature.
        feature_len = 0
        for interval in self.intervals:
            # HACK: +1 for EOL char. Need bx-python to provide raw_line itself 
            # b/c TableReader strips EOL characters, thus changing the line
            # length.
            feature_len += len( interval.raw_line ) + 1
        return feature_len
                
class GFFIntervalToBEDReaderWrapper( NiceReaderWrapper ):
    """ 
    Reader wrapper that reads GFF intervals/lines and automatically converts
    them to BED format. 
    """
    
    def parse_row( self, line ):
        # HACK: this should return a GFF interval, but bx-python operations 
        # require GenomicInterval objects and subclasses will not work.
        interval = GenomicInterval( self, line.split( "\t" ), self.chrom_col, self.start_col, \
                                    self.end_col, self.strand_col, self.default_strand, \
                                    fix_strand=self.fix_strand )
        interval = convert_gff_coords_to_bed( interval )
        return interval

class GFFReaderWrapper( NiceReaderWrapper ):
    """
    Reader wrapper for GFF files.
    
    Wrapper has two major functions:
    (1) group entries for GFF file (via group column), GFF3 (via id attribute), 
        or GTF (via gene_id/transcript id);
    (2) convert coordinates from GFF format--starting and ending coordinates 
        are 1-based, closed--to the 'traditional'/BED interval format--0 based, 
        half-open. This is useful when using GFF files as inputs to tools that 
        expect traditional interval format.
    """
    
    def __init__( self, reader, chrom_col=0, start_col=3, end_col=4, strand_col=6, score_col=5, \
                  fix_strand=False, **kwargs ):
        NiceReaderWrapper.__init__( self, reader, chrom_col=chrom_col, start_col=start_col, end_col=end_col, \
                                    strand_col=strand_col, fix_strand=fix_strand, **kwargs )
        # HACK: NiceReaderWrapper (bx-python) does not handle score_col yet, so store ourselves.
        self.score_col = score_col
        self.last_line = None
        self.cur_offset = 0
        self.seed_interval = None
    
    def parse_row( self, line ):
        interval = GFFInterval( self, line.split( "\t" ), self.chrom_col, self.start_col, \
                                self.end_col, self.strand_col, self.score_col, self.default_strand, \
                                fix_strand=self.fix_strand, raw_line=line )
        return interval
        
    def next( self ):
        """ Returns next GFFFeature. """
        
        #
        # Helper function.
        #
        
        def handle_parse_error( parse_error ):
            """ Actions to take when ParseError found. """
            if self.outstream:
               if self.print_delegate and hasattr(self.print_delegate,"__call__"):
                   self.print_delegate( self.outstream, e, self )
            self.skipped += 1
            # no reason to stuff an entire bad file into memmory
            if self.skipped < 10:
               self.skipped_lines.append( ( self.linenum, self.current_line, str( e ) ) )
               
            # For debugging, uncomment this to propogate parsing exceptions up. 
            # I.e. the underlying reason for an unexpected StopIteration exception 
            # can be found by uncommenting this. 
            # raise e
               
        #
        # Get next GFFFeature
        # 

        # If there is no seed interval, set one. Also, if there are no more 
        # intervals to read, this is where iterator dies.
        if not self.seed_interval:
            while not self.seed_interval:
                try:
                    self.seed_interval = GenomicIntervalReader.next( self )
                except ParseError, e:
                    handle_parse_error( e )
                    
        # If header or comment, clear seed interval and return it.
        if isinstance( self.seed_interval, ( Header, Comment ) ):
            return_val = self.seed_interval
            self.seed_interval = None
            return return_val
    
        # Initialize feature name from seed.
        feature_group = self.seed_interval.attributes.get( 'group', None ) # For GFF
        feature_id = self.seed_interval.attributes.get( 'id', None ) # For GFF3
        feature_gene_id = self.seed_interval.attributes.get( 'gene_id', None ) # For GTF
        feature_transcript_id = self.seed_interval.attributes.get( 'transcript_id', None ) # For GTF

        # Read all intervals associated with seed.
        feature_intervals = []
        feature_intervals.append( self.seed_interval )
        while True:
            try:
                interval = GenomicIntervalReader.next( self )
            except StopIteration, e:
                # No more intervals to read, but last feature needs to be 
                # returned.
                interval = None
                break
            except ParseError, e:
                handle_parse_error( e )
            
            # If interval not associated with feature, break.
            group = interval.attributes.get( 'group', None )
            if group and feature_group != group:
                break
            id = interval.attributes.get( 'id', None )
            if id and feature_id != id:
                break
            gene_id = interval.attributes.get( 'gene_id', None )
            transcript_id = interval.attributes.get( 'transcript_id', None )
            if ( transcript_id and transcript_id != feature_transcript_id ) or \
               ( gene_id and gene_id != feature_gene_id ):
                break
    
            # Interval associated with feature.
            feature_intervals.append( interval )
   
        # Last interval read is the seed for the next interval.
        self.seed_interval = interval
    
        # Return GFF feature with all intervals.    
        return GFFFeature( self, self.chrom_col, self.start_col, self.end_col, self.strand_col, \
                           self.score_col, self.default_strand, fix_strand=self.fix_strand, \
                           intervals=feature_intervals )
        

def convert_bed_coords_to_gff( interval ):
    """
    Converts an interval object's coordinates from BED format to GFF format. 
    Accepted object types include GenomicInterval and list (where the first 
    element in the list is the interval's start, and the second element is 
    the interval's end).
    """
    if type( interval ) is GenomicInterval:
        interval.start += 1
    elif type ( interval ) is list:
        interval[ 0 ] += 1
    return interval
    
def convert_gff_coords_to_bed( interval ):
    """
    Converts an interval object's coordinates from GFF format to BED format. 
    Accepted object types include GFFFeature, GenomicInterval, and list (where
    the first element in the list is the interval's start, and the second 
    element is the interval's end).
    """
    if isinstance( interval, GenomicInterval ):
        interval.start -= 1
        if isinstance( interval, GFFFeature ):
            for subinterval in interval.intervals:
                convert_gff_coords_to_bed( subinterval )
    elif type ( interval ) is list:
        interval[ 0 ] -= 1
    return interval
    
def parse_gff_attributes( attr_str ):
    """
    Parses a GFF/GTF attribute string and returns a dictionary of name-value 
    pairs. The general format for a GFF3 attributes string is 
        name1=value1;name2=value2
    The general format for a GTF attribute string is 
        name1 "value1" ; name2 "value2"
    The general format for a GFF attribute string is a single string that
    denotes the interval's group; in this case, method returns a dictionary 
    with a single key-value pair, and key name is 'group'
    """    
    attributes_list = attr_str.split(";")
    attributes = {}
    for name_value_pair in attributes_list:
        # Try splitting by space and, if necessary, by '=' sign.
        pair = name_value_pair.strip().split(" ")
        if len( pair ) == 1:
            pair = name_value_pair.strip().split("=")
        if len( pair ) == 1:
            # Could not split for some reason -- raise exception?
            continue
        if pair == '':
            continue
        name = pair[0].strip()
        if name == '':
            continue
        # Need to strip double quote from values
        value = pair[1].strip(" \"")
        attributes[ name ] = value
        
    if len( attributes ) == 0:
        # Could not split attributes string, so entire string must be 
        # 'group' attribute. This is the case for strictly GFF files.
        attributes['group'] = attr_str
    return attributes
    
def gff_attributes_to_str( attrs, gff_format ):
    """
    Convert GFF attributes to string. Supported formats are GFF3, GTF. 
    """
    if gff_format == 'GTF':
        format_string = '%s "%s"'
    elif gff_format == 'GFF3':
        format_string = '%s=%s'
    attrs_strs = []
    for name, value in attrs.items():
        attrs_strs.append( format_string % ( name, value ) )
    return " ; ".join( attrs_strs )
    