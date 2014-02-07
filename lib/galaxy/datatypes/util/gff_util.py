"""
Provides utilities for working with GFF files.
"""

import copy
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.intervals.io import *
from bx.tabular.io import Header, Comment
from galaxy.util.odict import odict

class GFFInterval( GenomicInterval ):
    """
    A GFF interval, including attributes. If file is strictly a GFF file,
    only attribute is 'group.'
    """
    def __init__( self, reader, fields, chrom_col=0, feature_col=2, start_col=3, end_col=4, \
                  strand_col=6, score_col=5, default_strand='.', fix_strand=False ):
        # HACK: GFF format allows '.' for strand but GenomicInterval does not. To get around this,
        # temporarily set strand and then unset after initing GenomicInterval.
        unknown_strand = False
        if not fix_strand and fields[ strand_col ] == '.':
            unknown_strand = True
            fields[ strand_col ] = '+'
        GenomicInterval.__init__( self, reader, fields, chrom_col, start_col, end_col, strand_col, \
                                  default_strand, fix_strand=fix_strand )
        if unknown_strand:
            self.strand = '.'
            self.fields[ strand_col ] = '.'

        # Handle feature, score column.
        self.feature_col = feature_col
        if self.feature_col >= self.nfields:
            raise MissingFieldError( "No field for feature_col (%d)" % feature_col )
        self.feature = self.fields[ self.feature_col ]
        self.score_col = score_col
        if self.score_col >= self.nfields:
            raise MissingFieldError( "No field for score_col (%d)" % score_col )
        self.score = self.fields[ self.score_col ]

        # GFF attributes.
        self.attributes = parse_gff_attributes( fields[8] )

    def copy( self ):
        return GFFInterval(self.reader, list( self.fields ), self.chrom_col, self.feature_col, self.start_col,
                           self.end_col, self.strand_col, self.score_col, self.strand)

class GFFFeature( GFFInterval ):
    """
    A GFF feature, which can include multiple intervals.
    """
    def __init__( self, reader, chrom_col=0, feature_col=2, start_col=3, end_col=4, \
                  strand_col=6, score_col=5, default_strand='.', fix_strand=False, intervals=[], \
                  raw_size=0 ):
        # Use copy so that first interval and feature do not share fields.
        GFFInterval.__init__( self, reader, copy.deepcopy( intervals[0].fields ), chrom_col, feature_col, \
                              start_col, end_col, strand_col, score_col, default_strand, \
                              fix_strand=fix_strand )
        self.intervals = intervals
        self.raw_size = raw_size
        # Use intervals to set feature attributes.
        for interval in self.intervals:
            # Error checking. NOTE: intervals need not share the same strand.
            if interval.chrom != self.chrom:
                raise ValueError( "interval chrom does not match self chrom: %s != %s" % \
                                  ( interval.chrom, self.chrom ) )
            # Set start, end of interval.
            if interval.start < self.start:
                self.start = interval.start
            if interval.end > self.end:
                self.end = interval.end

    def name( self ):
        """ Returns feature's name. """
        name = None
        # Preference for name: GTF, GFF3, GFF.
        for attr_name in [
                           # GTF:
                           'gene_id', 'transcript_id',
                           # GFF3:
                           'ID', 'id',
                           # GFF (TODO):
                           'group' ]:
            name = self.attributes.get( attr_name, None )
            if name is not None:
                break
        return name

    def copy( self ):
        intervals_copy = []
        for interval in self.intervals:
            intervals_copy.append( interval.copy() )
        return GFFFeature(self.reader, self.chrom_col, self.feature_col, self.start_col, self.end_col, self.strand_col,
                          self.score_col, self.strand, intervals=intervals_copy )

    def lines( self ):
        lines = []
        for interval in self.intervals:
            lines.append( '\t'.join( interval.fields ) )
        return lines


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

    1. group entries for GFF file (via group column), GFF3 (via id attribute),
       or GTF (via gene_id/transcript id);
    2. convert coordinates from GFF format--starting and ending coordinates
       are 1-based, closed--to the 'traditional'/BED interval format--0 based,
       half-open. This is useful when using GFF files as inputs to tools that
       expect traditional interval format.
    """

    def __init__( self, reader, chrom_col=0, feature_col=2, start_col=3, \
                  end_col=4, strand_col=6, score_col=5, fix_strand=False, convert_to_bed_coord=False, **kwargs ):
        NiceReaderWrapper.__init__( self, reader, chrom_col=chrom_col, start_col=start_col, end_col=end_col, \
                                    strand_col=strand_col, fix_strand=fix_strand, **kwargs )
        self.feature_col = feature_col
        self.score_col = score_col
        self.convert_to_bed_coord = convert_to_bed_coord
        self.last_line = None
        self.cur_offset = 0
        self.seed_interval = None
        self.seed_interval_line_len = 0

    def parse_row( self, line ):
        interval = GFFInterval( self, line.split( "\t" ), self.chrom_col, self.feature_col, \
                                self.start_col, self.end_col, self.strand_col, self.score_col, \
                                self.default_strand, fix_strand=self.fix_strand )
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
        raw_size = self.seed_interval_line_len

        # If there is no seed interval, set one. Also, if there are no more
        # intervals to read, this is where iterator dies.
        if not self.seed_interval:
            while not self.seed_interval:
                try:
                    self.seed_interval = GenomicIntervalReader.next( self )
                except ParseError, e:
                    handle_parse_error( e )
                # TODO: When no longer supporting python 2.4 use finally:
                #finally:
                raw_size += len( self.current_line )

        # If header or comment, clear seed interval and return it with its size.
        if isinstance( self.seed_interval, ( Header, Comment ) ):
            return_val = self.seed_interval
            return_val.raw_size = len( self.current_line )
            self.seed_interval = None
            self.seed_interval_line_len = 0
            return return_val

        # Initialize feature identifier from seed.
        feature_group = self.seed_interval.attributes.get( 'group', None ) # For GFF
        # For GFF3
        feature_id = self.seed_interval.attributes.get( 'ID', None )
        feature_parent_id = self.seed_interval.attributes.get( 'Parent', None )
        # For GTF.
        feature_gene_id = self.seed_interval.attributes.get( 'gene_id', None )
        feature_transcript_id = self.seed_interval.attributes.get( 'transcript_id', None )

        # Read all intervals associated with seed.
        feature_intervals = []
        feature_intervals.append( self.seed_interval )
        while True:
            try:
                interval = GenomicIntervalReader.next( self )
                raw_size += len( self.current_line )
            except StopIteration, e:
                # No more intervals to read, but last feature needs to be
                # returned.
                interval = None
                raw_size += len( self.current_line )
                break
            except ParseError, e:
                handle_parse_error( e )
                raw_size += len( self.current_line )
                continue
            # TODO: When no longer supporting python 2.4 use finally:
            #finally:
            #raw_size += len( self.current_line )

            # Ignore comments.
            if isinstance( interval, Comment ):
                continue

            # Determine if interval is part of feature.
            part_of = False
            group = interval.attributes.get( 'group', None )
            # GFF test:
            if group and feature_group == group:
                part_of = True
            # GFF3 test:
            parent_id = interval.attributes.get( 'Parent', None )
            cur_id = interval.attributes.get( 'ID', None )
            if ( cur_id and cur_id == feature_id ) or ( parent_id and parent_id == feature_id ):
                part_of = True
            # GTF test:
            transcript_id = interval.attributes.get( 'transcript_id', None )
            if transcript_id and transcript_id == feature_transcript_id:
                part_of = True

            # If interval is not part of feature, clean up and break.
            if not part_of:
                # Adjust raw size because current line is not part of feature.
                raw_size -= len( self.current_line )
                break

            # Interval associated with feature.
            feature_intervals.append( interval )

        # Last interval read is the seed for the next interval.
        self.seed_interval = interval
        self.seed_interval_line_len = len( self.current_line )

        # Return feature.
        feature = GFFFeature( self, self.chrom_col, self.feature_col, self.start_col, \
                              self.end_col, self.strand_col, self.score_col, \
                              self.default_strand, fix_strand=self.fix_strand, \
                              intervals=feature_intervals, raw_size=raw_size )

        # Convert to BED coords?
        if self.convert_to_bed_coord:
            convert_gff_coords_to_bed( feature )

        return feature

def convert_bed_coords_to_gff( interval ):
    """
    Converts an interval object's coordinates from BED format to GFF format.
    Accepted object types include GenomicInterval and list (where the first
    element in the list is the interval's start, and the second element is
    the interval's end).
    """
    if isinstance( interval, GenomicInterval ):
        interval.start += 1
        if isinstance( interval, GFFFeature ):
            for subinterval in interval.intervals:
                convert_bed_coords_to_gff( subinterval )
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
        # Try splitting by '=' (GFF3) first because spaces are allowed in GFF3
        # attribute; next, try double quotes for GTF.
        pair = name_value_pair.strip().split("=")
        if len( pair ) == 1:
            pair = name_value_pair.strip().split("\"")
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
        # Convert group (GFF) and ID, parent (GFF3) attributes to transcript_id, gene_id
        id_attr = None
        if 'group' in attrs:
            id_attr = 'group'
        elif 'ID' in attrs:
            id_attr = 'ID'
        elif 'Parent' in attrs:
            id_attr = 'Parent'
        if id_attr:
            attrs['transcript_id'] = attrs['gene_id'] = attrs[id_attr]
    elif gff_format == 'GFF3':
        format_string = '%s=%s'
    attrs_strs = []
    for name, value in attrs.items():
        attrs_strs.append( format_string % ( name, value ) )
    return " ; ".join( attrs_strs )

def read_unordered_gtf( iterator, strict=False ):
    """
    Returns GTF features found in an iterator. GTF lines need not be ordered
    or clustered for reader to work. Reader returns GFFFeature objects sorted
    by transcript_id, chrom, and start position.
    """

    # -- Get function that generates line/feature key. --

    get_transcript_id = lambda fields: parse_gff_attributes( fields[8] )[ 'transcript_id' ]
    if strict:
        # Strict GTF parsing uses transcript_id only to group lines into feature.
        key_fn = get_transcript_id
    else:
        # Use lenient parsing where chromosome + transcript_id is the key. This allows
        # transcripts with same ID on different chromosomes; this occurs in some popular
        # datasources, such as RefGenes in UCSC.
        key_fn = lambda fields: fields[0] + '_' + get_transcript_id( fields )


    # Aggregate intervals by transcript_id and collect comments.
    feature_intervals = odict()
    comments = []
    for count, line in enumerate( iterator ):
        if line.startswith( '#' ):
            comments.append( Comment( line ) )
            continue

        line_key = key_fn( line.split('\t') )
        if line_key in feature_intervals:
            feature = feature_intervals[ line_key ]
        else:
            feature = []
            feature_intervals[ line_key ] = feature
        feature.append( GFFInterval( None, line.split( '\t' ) ) )

    # Create features.
    chroms_features = {}
    for count, intervals in enumerate( feature_intervals.values() ):
        # Sort intervals by start position.
        intervals.sort( lambda a,b: cmp( a.start, b.start ) )
        feature = GFFFeature( None, intervals=intervals )
        if feature.chrom not in chroms_features:
            chroms_features[ feature.chrom ] = []
        chroms_features[ feature.chrom ].append( feature )

    # Sort features by chrom, start position.
    chroms_features_sorted = []
    for chrom_features in chroms_features.values():
        chroms_features_sorted.append( chrom_features )
    chroms_features_sorted.sort( lambda a,b: cmp( a[0].chrom, b[0].chrom ) )
    for features in chroms_features_sorted:
        features.sort( lambda a,b: cmp( a.start, b.start ) )

    # Yield comments first, then features.
    # FIXME: comments can appear anywhere in file, not just the beginning.
    # Ideally, then comments would be associated with features and output
    # just before feature/line.
    for comment in comments:
        yield comment

    for chrom_features in chroms_features_sorted:
        for feature in chrom_features:
            yield feature

