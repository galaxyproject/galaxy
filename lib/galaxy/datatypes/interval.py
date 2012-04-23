"""
Interval datatypes
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import logging, os, sys, tempfile
import data
from galaxy import util
from galaxy.datatypes.sniff import *
from galaxy.web import url_for
import urllib
from bx.intervals.io import *
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.util.gff_util import parse_gff_attributes
import math

log = logging.getLogger(__name__)

# Contains the meta columns and the words that map to it; list aliases on the
# right side of the : in decreasing order of priority
alias_spec = { 
    'chromCol'  : [ 'chrom' , 'CHROMOSOME' , 'CHROM', 'Chromosome Name' ],  
    'startCol'  : [ 'start' , 'START', 'chromStart', 'txStart', 'Start Position (bp)' ],
    'endCol'    : [ 'end'   , 'END'  , 'STOP', 'chromEnd', 'txEnd', 'End Position (bp)'  ], 
    'strandCol' : [ 'strand', 'STRAND', 'Strand' ],
    'nameCol'   : [ 'name', 'NAME', 'Name', 'name2', 'NAME2', 'Name2', 'Ensembl Gene ID', 'Ensembl Transcript ID', 'Ensembl Peptide ID' ]
}

# a little faster lookup
alias_helper = {}
for key, value in alias_spec.items():
    for elem in value:
        alias_helper[elem] = key

# Constants for configuring viewport generation: If a line is greater than
# VIEWPORT_MAX_READS_PER_LINE * VIEWPORT_READLINE_BUFFER_SIZE bytes in size,
# then we will not generate a viewport for that dataset
VIEWPORT_READLINE_BUFFER_SIZE = 1048576 # 1MB
VIEWPORT_MAX_READS_PER_LINE = 10 

class Interval( Tabular ):
    """Tab delimited data containing interval information"""
    file_ext = "interval"
    line_class = "region"

    """Add metadata elements"""
    MetadataElement( name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter )
    MetadataElement( name="endCol", default=3, desc="End column", param=metadata.ColumnParameter )
    MetadataElement( name="strandCol", desc="Strand column (click box & select)", param=metadata.ColumnParameter, optional=True, no_value=0 )
    MetadataElement( name="nameCol", desc="Name/Identifier column (click box & select)", param=metadata.ColumnParameter, optional=True, no_value=0 )
    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )

    def __init__(self, **kwd):
        """Initialize interval datatype, by adding UCSC display apps"""
        Tabular.__init__(self, **kwd)
        self.add_display_app ( 'ucsc', 'display at UCSC', 'as_ucsc_display_file', 'ucsc_links' )
    def init_meta( self, dataset, copy_from=None ):
        Tabular.init_meta( self, dataset, copy_from=copy_from )
    def set_meta( self, dataset, overwrite = True, first_line_is_header = False, **kwd ):
        """Tries to guess from the line the location number of the column for the chromosome, region start-end and strand"""
        Tabular.set_meta( self, dataset, overwrite = overwrite, skip = 0 )
        if dataset.has_data():
            empty_line_count = 0
            num_check_lines = 100 # only check up to this many non empty lines
            for i, line in enumerate( file( dataset.file_name ) ):
                line = line.rstrip( '\r\n' )
                if line:
                    if ( first_line_is_header or line[0] == '#' ):
                        self.init_meta( dataset )
                        line = line.strip( '#' )
                        elems = line.split( '\t' )
                        for meta_name, header_list in alias_spec.iteritems():
                            for header_val in header_list:
                                if header_val in elems:
                                    #found highest priority header to meta_name
                                    setattr( dataset.metadata, meta_name, elems.index( header_val ) + 1 )
                                    break #next meta_name
                        break  # Our metadata is set, so break out of the outer loop
                    else: 
                        # Header lines in Interval files are optional. For example, BED is Interval but has no header.
                        # We'll make a best guess at the location of the metadata columns.
                        metadata_is_set = False
                        elems = line.split( '\t' )
                        if len( elems ) > 2:
                            for str in data.col1_startswith:
                                if line.lower().startswith( str ):
                                    if overwrite or not dataset.metadata.element_is_set( 'chromCol' ):
                                        dataset.metadata.chromCol = 1
                                    try:
                                        int( elems[1] )
                                        if overwrite or not dataset.metadata.element_is_set( 'startCol' ):
                                            dataset.metadata.startCol = 2
                                    except:
                                        pass # Metadata default will be used
                                    try:
                                        int( elems[2] )
                                        if overwrite or not dataset.metadata.element_is_set( 'endCol' ):
                                            dataset.metadata.endCol = 3
                                    except:
                                        pass # Metadata default will be used
                                    #we no longer want to guess that this column is the 'name', name must now be set manually for interval files
                                    #we will still guess at the strand, as we can make a more educated guess
                                    #if len( elems ) > 3:
                                    #    try:
                                    #        int( elems[3] )
                                    #    except:
                                    #        if overwrite or not dataset.metadata.element_is_set( 'nameCol' ):
                                    #            dataset.metadata.nameCol = 4 
                                    if len( elems ) < 6 or elems[5] not in data.valid_strand:
                                        if overwrite or not dataset.metadata.element_is_set(  'strandCol' ):
                                            dataset.metadata.strandCol = 0
                                    else:
                                        if overwrite or not dataset.metadata.element_is_set( 'strandCol' ):
                                            dataset.metadata.strandCol = 6
                                    metadata_is_set = True
                                    break
                        if metadata_is_set or ( i - empty_line_count ) > num_check_lines:
                            break # Our metadata is set or we examined 100 non-empty lines, so break out of the outer loop
                else:
                    empty_line_count += 1
    def displayable( self, dataset ):
        try:
            return dataset.has_data() \
                and dataset.state == dataset.states.OK \
                and dataset.metadata.columns > 0 \
                and dataset.metadata.data_lines != 0 \
                and dataset.metadata.chromCol \
                and dataset.metadata.startCol \
                and dataset.metadata.endCol
        except:
            return False

    def get_estimated_display_viewport( self, dataset, chrom_col = None, start_col = None, end_col = None ):
        """Return a chrom, start, stop tuple for viewing a file."""
        viewport_feature_count = 100 # viewport should check at least 100 features; excludes comment lines
        max_line_count = max( viewport_feature_count, 500 ) # maximum number of lines to check; includes comment lines
        if not self.displayable( dataset ):
            return ( None, None, None )
        try:
            # If column indexes were not passwed, determine from metadata
            if chrom_col is None:
                chrom_col = int( dataset.metadata.chromCol ) - 1
            if start_col is None:
                start_col = int( dataset.metadata.startCol ) - 1
            if end_col is None:
                end_col = int( dataset.metadata.endCol ) - 1
            # Scan lines of file to find a reasonable chromosome and range
            chrom = None 
            start = sys.maxint 
            end = 0
            max_col = max( chrom_col, start_col, end_col )
            fh = open( dataset.file_name )
            while True:
                line = fh.readline( VIEWPORT_READLINE_BUFFER_SIZE )
                # Stop if at end of file
                if not line: 
                    break
                # Skip comment lines
                if not line.startswith( '#' ):
                    try:
                        fields = line.rstrip().split( '\t' )
                        if len( fields ) > max_col:
                            if chrom is None or chrom == fields[ chrom_col ]:
                                start = min( start, int( fields[ start_col ] ) )
                                end = max( end, int( fields[ end_col ] ) )
                                # Set chrom last, in case start and end are not integers
                                chrom = fields[ chrom_col ] 
                            viewport_feature_count -= 1
                    except Exception, e:
                        # Most likely a non-integer field has been encountered
                        # for start / stop. Just ignore and make sure we finish
                        # reading the line and decrementing the counters.
                        pass
                # Make sure we are at the next new line
                readline_count = VIEWPORT_MAX_READS_PER_LINE
                while line.rstrip( '\n\r' ) == line:
                    assert readline_count > 0, Exception( 'Viewport readline count exceeded for dataset %s.' % dataset.id )
                    line = fh.readline( VIEWPORT_READLINE_BUFFER_SIZE )
                    if not line: break #EOF
                    readline_count -= 1
                max_line_count -= 1
                if not viewport_feature_count or not max_line_count:
                    #exceeded viewport or total line count to check
                    break
            if chrom is not None:
                return ( chrom, str( start ), str( end ) ) # Necessary to return strings?
        except Exception, e:
            # Unexpected error, possibly missing metadata
            log.exception( "Exception caught attempting to generate viewport for dataset '%d'", dataset.id )
        return ( None, None, None ) 

    def as_ucsc_display_file( self, dataset, **kwd ):
        """Returns file contents with only the bed data"""
        fd, temp_name = tempfile.mkstemp()
        c, s, e, t, n = dataset.metadata.chromCol, dataset.metadata.startCol, dataset.metadata.endCol, dataset.metadata.strandCol or 0, dataset.metadata.nameCol or 0
        c, s, e, t, n  = int(c)-1, int(s)-1, int(e)-1, int(t)-1, int(n)-1
        if t >= 0: # strand column (should) exists
            for i, elems in enumerate( util.file_iter(dataset.file_name) ):
                strand = "+"
                name = "region_%i" % i
                if n >= 0 and n < len( elems ): name = elems[n]
                if t<len(elems): strand = elems[t]
                tmp = [ elems[c], elems[s], elems[e], name, '0', strand ]
                os.write(fd, '%s\n' % '\t'.join(tmp) )
        elif n >= 0: # name column (should) exists
            for i, elems in enumerate( util.file_iter(dataset.file_name) ):
                name = "region_%i" % i
                if n >= 0 and n < len( elems ): name = elems[n]
                tmp = [ elems[c], elems[s], elems[e], name ]
                os.write(fd, '%s\n' % '\t'.join(tmp) )
        else:
            for elems in util.file_iter(dataset.file_name):
                tmp = [ elems[c], elems[s], elems[e] ]
                os.write(fd, '%s\n' % '\t'.join(tmp) )    
        os.close(fd)
        return open(temp_name)
    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return Tabular.make_html_table( self, dataset, column_parameter_alias={'chromCol':'Chrom', 'startCol':'Start', 'endCol':'End', 'strandCol':'Strand', 'nameCol':'Name'} )
    def ucsc_links( self, dataset, type, app, base_url ):
        """
        Generate links to UCSC genome browser sites based on the dbkey
        and content of dataset.
        """
        # Filter UCSC sites to only those that are supported by this build and
        # enabled.
        valid_sites = [ ( name, url ) 
                        for name, url in util.get_ucsc_by_build( dataset.dbkey ) 
                        if name in app.config.ucsc_display_sites ]
        if not valid_sites:
            return []
        # If there are any valid sites, we need to generate the estimated
        # viewport
        chrom, start, stop = self.get_estimated_display_viewport( dataset )
        if chrom is None:
            return []
        # Accumulate links for valid sites
        ret_val = []
        for site_name, site_url in valid_sites:
            internal_url = url_for( controller='/dataset', dataset_id=dataset.id, 
                                    action='display_at', filename='ucsc_' + site_name )
            display_url = urllib.quote_plus( "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at" 
                    % (base_url, url_for( controller='root' ), dataset.id, type) )
            redirect_url = urllib.quote_plus( "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s" 
                    % (site_url, dataset.dbkey, chrom, start, stop ) )
            link = '%s?redirect_url=%s&display_url=%s' % ( internal_url, redirect_url, display_url )
            ret_val.append( ( site_name, link ) )
        return ret_val
    def validate( self, dataset ):
        """Validate an interval file using the bx GenomicIntervalReader"""
        errors = list()
        c, s, e, t = dataset.metadata.chromCol, dataset.metadata.startCol, dataset.metadata.endCol, dataset.metadata.strandCol 
        c, s, e, t = int(c)-1, int(s)-1, int(e)-1, int(t)-1
        infile = open(dataset.file_name, "r")
        reader = GenomicIntervalReader(
            infile,
            chrom_col = c,
            start_col = s,
            end_col = e,
            strand_col = t)

        while True:
            try:
                reader.next()
            except ParseError, e:
                errors.append(e)
            except StopIteration:
                infile.close()
                return errors

    def repair_methods( self, dataset ):
        """Return options for removing errors along with a description"""
        return [("lines","Remove erroneous lines")]

    def sniff( self, filename ):
        """
        Checks for 'intervalness'
    
        This format is mostly used by galaxy itself.  Valid interval files should include
        a valid header comment, but this seems to be loosely regulated.
        
        >>> fname = get_test_fname( 'test_space.txt' )
        >>> Interval().sniff( fname )
        False
        >>> fname = get_test_fname( 'interval.interval' )
        >>> Interval().sniff( fname )
        True
        """
        headers = get_headers( filename, '\t' )
        try:
            """
            If we got here, we already know the file is_column_based and is not bed,
            so we'll just look for some valid data.
            """
            for hdr in headers:
                if hdr and not hdr[0].startswith( '#' ):
                    if len(hdr) < 3:
                        return False
                    try:
                        # Assume chrom start and end are in column positions 1 and 2
                        # respectively ( for 0 based columns )
                        check = int( hdr[1] )
                        check = int( hdr[2] )
                    except:
                        return False
            return True
        except:
            return False

    def get_track_window(self, dataset, data, start, end):
        """
        Assumes the incoming track data is sorted already.
        """
        window = list()
        for record in data:
            fields = record.rstrip("\n\r").split("\t")
            record_chrom = fields[dataset.metadata.chromCol-1]
            record_start = int(fields[dataset.metadata.startCol-1])
            record_end = int(fields[dataset.metadata.endCol-1])
            if record_start < end and record_end > start:
                window.append( (record_chrom, record_start, record_end) )  #Yes I did want to use a generator here, but it doesn't work downstream
        return window

    def get_track_resolution( self, dataset, start, end):
        return None
        
    def get_track_type( self ):
        return "FeatureTrack", {"data": "tabix", "index": "summary_tree"}

class BedGraph( Interval ):
    """Tab delimited chrom/start/end/datavalue dataset"""

    file_ext = "bedgraph"

    def get_track_type( self ):
        return "LineTrack", {"data": "array_tree"}
        
    def as_ucsc_display_file( self, dataset, **kwd ):
        """
            Returns file contents as is with no modifications. 
            TODO: this is a functional stub and will need to be enhanced moving forward to provide additional support for bedgraph.
        """
        return open( dataset.file_name )
        
    def get_estimated_display_viewport( self, dataset, chrom_col = 0, start_col = 1, end_col = 2 ):
        """
            Set viewport based on dataset's first 100 lines.
        """
        return Interval.get_estimated_display_viewport( self, dataset, chrom_col = chrom_col, start_col = start_col, end_col = end_col )

class Bed( Interval ):
    """Tab delimited data in BED format"""
    file_ext = "bed"

    """Add metadata elements"""
    MetadataElement( name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter )
    MetadataElement( name="endCol", default=3, desc="End column", param=metadata.ColumnParameter )
    MetadataElement( name="strandCol", desc="Strand column (click box & select)", param=metadata.ColumnParameter, optional=True, no_value=0 )
    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="viz_filter_cols", desc="Score column for visualization", default=[4], param=metadata.ColumnParameter, multiple=True )
    ###do we need to repeat these? they are the same as should be inherited from interval type

    def set_meta( self, dataset, overwrite = True, **kwd ):
        """Sets the metadata information for datasets previously determined to be in bed format."""
        i = 0
        if dataset.has_data():
            for i, line in enumerate( file(dataset.file_name) ):
                metadata_set = False
                line = line.rstrip('\r\n')
                if line and not line.startswith('#'):
                    elems = line.split('\t')
                    if len(elems) > 2:
                        for startswith in data.col1_startswith:
                            if line.lower().startswith( startswith ):
                                if len( elems ) > 3:
                                    if overwrite or not dataset.metadata.element_is_set( 'nameCol' ):
                                        dataset.metadata.nameCol = 4
                                if len(elems) < 6:
                                    if overwrite or not dataset.metadata.element_is_set( 'strandCol' ):
                                        dataset.metadata.strandCol = 0
                                else:
                                    if overwrite or not dataset.metadata.element_is_set( 'strandCol' ):
                                        dataset.metadata.strandCol = 6
                                metadata_set = True
                                break
                if metadata_set: break
            Tabular.set_meta( self, dataset, overwrite = overwrite, skip = i )
    
    def as_ucsc_display_file( self, dataset, **kwd ):
        """Returns file contents with only the bed data. If bed 6+, treat as interval."""
        for line in open(dataset.file_name):
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            fields = line.split('\t')
            """check to see if this file doesn't conform to strict genome browser accepted bed"""
            try:
                if len(fields) > 12:
                    return Interval.as_ucsc_display_file(self, dataset) #too many fields
                if len(fields) > 6:
                    int(fields[6])
                    if len(fields) > 7:
                        int(fields[7])
                        if len(fields) > 8:
                            if int(fields[8]) != 0:
                                return Interval.as_ucsc_display_file(self, dataset)
                            if len(fields) > 9:
                                int(fields[9])
                                if len(fields) > 10:
                                    fields2 = fields[10].rstrip(",").split(",") #remove trailing comma and split on comma
                                    for field in fields2: 
                                        int(field)
                                    if len(fields) > 11:
                                        fields2 = fields[11].rstrip(",").split(",") #remove trailing comma and split on comma
                                        for field in fields2:
                                            int(field)
            except: return Interval.as_ucsc_display_file(self, dataset)
            #only check first line for proper form
            break
            
        try: return open(dataset.file_name)
        except: return "This item contains no content"

    def sniff( self, filename ):
        """
        Checks for 'bedness'
        
        BED lines have three required fields and nine additional optional fields. 
        The number of fields per line must be consistent throughout any single set of data in 
        an annotation track.  The order of the optional fields is binding: lower-numbered 
        fields must always be populated if higher-numbered fields are used.  The data type of
        all 12 columns is:
        1-str, 2-int, 3-int, 4-str, 5-int, 6-str, 7-int, 8-int, 9-int or list, 10-int, 11-list, 12-list
        
        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format1
        
        >>> fname = get_test_fname( 'test_tab.bed' )
        >>> Bed().sniff( fname )
        True
        >>> fname = get_test_fname( 'interval1.bed' )
        >>> Bed().sniff( fname )
        True
        >>> fname = get_test_fname( 'complete.bed' )
        >>> Bed().sniff( fname )
        True
        """
        headers = get_headers( filename, '\t' )
        try:
            if not headers: return False
            for hdr in headers:
                if (hdr[0] == '' or hdr[0].startswith( '#' )):
                    continue
                valid_col1 = False
                if len(hdr) < 3 or len(hdr) > 12:
                    return False
                for str in data.col1_startswith:
                    if hdr[0].lower().startswith(str):
                        valid_col1 = True
                        break
                if valid_col1:
                    try:
                        int( hdr[1] )
                        int( hdr[2] )
                    except: 
                        return False
                    if len( hdr ) > 4:
                        #hdr[3] is a string, 'name', which defines the name of the BED line - difficult to test for this.
                        #hdr[4] is an int, 'score', a score between 0 and 1000.
                        try:
                            if int( hdr[4] ) < 0 or int( hdr[4] ) > 1000: return False
                        except:
                            return False
                    if len( hdr ) > 5:
                        #hdr[5] is strand
                        if hdr[5] not in data.valid_strand: return False
                    if len( hdr ) > 6:
                        #hdr[6] is thickStart, the starting position at which the feature is drawn thickly.
                        try: int( hdr[6] )
                        except: return False
                    if len( hdr ) > 7:
                        #hdr[7] is thickEnd, the ending position at which the feature is drawn thickly
                        try: int( hdr[7] )
                        except: return False
                    if len( hdr ) > 8:
                        #hdr[8] is itemRgb, an RGB value of the form R,G,B (e.g. 255,0,0).  However, this could also be an int (e.g., 0)
                        try: int( hdr[8] )
                        except:
                            try: hdr[8].split(',')
                            except: return False
                    if len( hdr ) > 9:
                        #hdr[9] is blockCount, the number of blocks (exons) in the BED line.
                        try: block_count = int( hdr[9] )
                        except: return False
                    if len( hdr ) > 10:
                        #hdr[10] is blockSizes - A comma-separated list of the block sizes.
                        #Sometimes the blosck_sizes and block_starts lists end in extra commas
                        try: block_sizes = hdr[10].rstrip(',').split(',')
                        except: return False
                    if len( hdr ) > 11:
                        #hdr[11] is blockStarts - A comma-separated list of block starts.
                        try: block_starts = hdr[11].rstrip(',').split(',')
                        except: return False
                        if len(block_sizes) != block_count or len(block_starts) != block_count: return False   
                else: return False
            return True
        except: return False
    
    def get_track_type( self ):
        return "FeatureTrack", {"data": "tabix", "index": "summary_tree"}

class BedStrict( Bed ):
    """Tab delimited data in strict BED format - no non-standard columns allowed"""

    file_ext = "bedstrict"
    
    #no user change of datatype allowed
    allow_datatype_change = False

    #Read only metadata elements
    MetadataElement( name="chromCol", default=1, desc="Chrom column", readonly=True, param=metadata.MetadataParameter )
    MetadataElement( name="startCol", default=2, desc="Start column", readonly=True, param=metadata.MetadataParameter ) #TODO: start and end should be able to be set to these or the proper thick[start/end]?
    MetadataElement( name="endCol", default=3, desc="End column", readonly=True, param=metadata.MetadataParameter )
    MetadataElement( name="strandCol", desc="Strand column (click box & select)", readonly=True, param=metadata.MetadataParameter, no_value=0, optional=True )
    MetadataElement( name="nameCol", desc="Name/Identifier column (click box & select)", readonly=True, param=metadata.MetadataParameter, no_value=0, optional=True )
    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )
    
    def __init__( self, **kwd ):
        Tabular.__init__( self, **kwd )
        self.clear_display_apps() #only new style display applications for this datatype
    
    def set_meta( self, dataset, overwrite = True, **kwd ):
        Tabular.set_meta( self, dataset, overwrite = overwrite, **kwd) #need column count first
        if dataset.metadata.columns >= 4:
            dataset.metadata.nameCol = 4
            if dataset.metadata.columns >= 6:
                dataset.metadata.strandCol = 6
    
    def sniff( self, filename ):
        return False #NOTE: This would require aggressively validating the entire file

class Bed6( BedStrict ):
    """Tab delimited data in strict BED format - no non-standard columns allowed; column count forced to 6"""

    file_ext = "bed6"

class Bed12( BedStrict ):
    """Tab delimited data in strict BED format - no non-standard columns allowed; column count forced to 12"""

    file_ext = "bed12"

class _RemoteCallMixin:
    def _get_remote_call_url( self, redirect_url, site_name, dataset, type, app, base_url ):
        """Retrieve the URL to call out to an external site and retrieve data.
        This routes our external URL through a local galaxy instance which makes
        the data available, followed by redirecting to the remote site with a
        link back to the available information.
        """
        internal_url = "%s" % url_for( controller='dataset', dataset_id=dataset.id, action='display_at', filename='%s_%s' % ( type, site_name ) )
        base_url = app.config.get( "display_at_callback", base_url )
        display_url = urllib.quote_plus( "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at" % \
                                         ( base_url, url_for( controller='root' ), dataset.id, type ) )
        link = '%s?redirect_url=%s&display_url=%s' % ( internal_url, redirect_url, display_url )
        return link

class Gff( Tabular, _RemoteCallMixin ):
    """Tab delimited data in Gff format"""
    file_ext = "gff"
    column_names = [ 'Seqname', 'Source', 'Feature', 'Start', 'End', 'Score', 'Strand', 'Frame', 'Group' ]

    """Add metadata elements"""
    MetadataElement( name="columns", default=9, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_types", default=['str','str','str','int','int','int','str','str','str'], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False )
    
    def __init__( self, **kwd ):
        """Initialize datatype, by adding GBrowse display app"""
        Tabular.__init__(self, **kwd)
        self.add_display_app( 'ucsc', 'display at UCSC', 'as_ucsc_display_file', 'ucsc_links' )
        self.add_display_app( 'gbrowse', 'display in Gbrowse', 'as_gbrowse_display_file', 'gbrowse_links' )
    def set_meta( self, dataset, overwrite = True, **kwd ):
        i = 0
        for i, line in enumerate( file ( dataset.file_name ) ):
            line = line.rstrip('\r\n')
            if line and not line.startswith( '#' ):
                elems = line.split( '\t' )
                if len(elems) == 9:
                    try:
                        int( elems[3] )
                        int( elems[4] )
                        break
                    except:
                        pass
        Tabular.set_meta( self, dataset, overwrite = overwrite, skip = i )
    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return Tabular.make_html_table( self, dataset, column_names=self.column_names )
    def get_estimated_display_viewport( self, dataset ):
        """
        Return a chrom, start, stop tuple for viewing a file.  There are slight differences between gff 2 and gff 3
        formats.  This function should correctly handle both...
        """
        viewport_feature_count = 100 # viewport should check at least 100 features; excludes comment lines
        max_line_count = max( viewport_feature_count, 500 ) # maximum number of lines to check; includes comment lines
        if self.displayable( dataset ):
            try:
                seqid = None 
                start = sys.maxint 
                stop = 0
                fh = open( dataset.file_name )
                while True:
                    line = fh.readline( VIEWPORT_READLINE_BUFFER_SIZE )
                    if not line: break #EOF
                    try:
                        if line.startswith( '##sequence-region' ): # ##sequence-region IV 6000000 6030000
                            elems = line.rstrip( '\n\r' ).split()
                            if len( elems ) > 3:
                                # line looks like:
                                # ##sequence-region   ctg123 1 1497228 
                                seqid = elems[1] # IV
                                start = int( elems[2] )# 6000000
                                stop = int( elems[3] ) # 6030000
                                break #use location declared in file
                            elif len( elems ) == 2 and elems[1].find( '..' ) > 0:
                                # line looks like this:
                                # ##sequence-region X:120000..140000
                                elems = elems[1].split( ':' )
                                seqid = elems[0]
                                start = int( elems[1].split( '..' )[0] )
                                stop = int( elems[1].split( '..' )[1] )
                                break #use location declared in file
                            else:
                                log.exception( "line (%s) uses an unsupported ##sequence-region definition." % str( line ) )
                                #break #no break, if bad definition, we try another method
                        elif line.startswith("browser position"):
                            # Allow UCSC style browser and track info in the GFF file
                            pos_info = line.split()[-1]
                            seqid, startend = pos_info.split(":")
                            start, stop = map( int, startend.split("-") )
                            break #use location declared in file
                        elif True not in map( line.startswith, ( '#', 'track', 'browser' ) ):# line.startswith() does not accept iterator in python2.4
                            viewport_feature_count -= 1
                            elems = line.rstrip( '\n\r' ).split( '\t' )
                            if len( elems ) > 3:
                                if not seqid:
                                    # We can only set the viewport for a single chromosome
                                    seqid = elems[0]
                                if seqid == elems[0]:
                                    # Make sure we have not spanned chromosomes
                                    start = min( start, int( elems[3] ) )
                                    stop = max( stop, int( elems[4] ) )
                    except:
                        #most likely start/stop is not an int or not enough fields
                        pass
                    #make sure we are at the next new line
                    readline_count = VIEWPORT_MAX_READS_PER_LINE
                    while line.rstrip( '\n\r' ) == line:
                        assert readline_count > 0, Exception( 'Viewport readline count exceeded for dataset %s.' % dataset.id )
                        line = fh.readline( VIEWPORT_READLINE_BUFFER_SIZE )
                        if not line: break #EOF
                        readline_count -= 1
                    max_line_count -= 1
                    if not viewport_feature_count or not max_line_count:
                        #exceeded viewport or total line count to check
                        break
                if seqid is not None:
                    return ( seqid, str( start ), str( stop ) ) #Necessary to return strings?
            except Exception, e:
                #unexpected error
                log.exception( str( e ) )
        return ( None, None, None ) #could not determine viewport
    def ucsc_links( self, dataset, type, app, base_url ):
        ret_val = []
        seqid, start, stop = self.get_estimated_display_viewport( dataset )
        if seqid is not None:
            for site_name, site_url in util.get_ucsc_by_build( dataset.dbkey ):
                if site_name in app.config.ucsc_display_sites:
                    redirect_url = urllib.quote_plus(
                            "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s" %
                            ( site_url, dataset.dbkey, seqid, start, stop ) )
                    link = self._get_remote_call_url( redirect_url, site_name, dataset, type, app, base_url )
                    ret_val.append( ( site_name, link ) )
        return ret_val
    def gbrowse_links( self, dataset, type, app, base_url ):
        ret_val = []
        seqid, start, stop = self.get_estimated_display_viewport( dataset )
        if seqid is not None:
            for site_name, site_url in util.get_gbrowse_sites_by_build( dataset.dbkey ):
                if site_name in app.config.gbrowse_display_sites:
                    if seqid.startswith( 'chr' ) and len ( seqid ) > 3:
                        seqid = seqid[3:]
                    redirect_url = urllib.quote_plus( "%s/?q=%s:%s..%s&eurl=%%s" % ( site_url, seqid, start, stop ) )
                    link = self._get_remote_call_url( redirect_url, site_name, dataset, type, app, base_url )
                    ret_val.append( ( site_name, link ) )
        return ret_val
    def sniff( self, filename ):
        """
        Determines whether the file is in gff format
        
        GFF lines have nine required fields that must be tab-separated.
        
        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format3
        
        >>> fname = get_test_fname( 'gff_version_3.gff' )
        >>> Gff().sniff( fname )
        False
        >>> fname = get_test_fname( 'test.gff' )
        >>> Gff().sniff( fname )
        True
        """
        headers = get_headers( filename, '\t' )
        try:
            if len(headers) < 2:
                return False
            for hdr in headers:
                if hdr and hdr[0].startswith( '##gff-version' ) and hdr[0].find( '2' ) < 0:
                    return False
                if hdr and hdr[0] and not hdr[0].startswith( '#' ):
                    if len(hdr) != 9:
                        return False
                    try:
                        int( hdr[3] )
                        int( hdr[4] )
                    except:
                        return False
                    if hdr[5] != '.':
                        try:
                            score = float( hdr[5] )
                        except:
                            return False
                    if hdr[6] not in data.valid_strand:
                        return False
            return True
        except:
            return False
            
    def get_track_type( self ):
        return "FeatureTrack", {"data": "interval_index", "index": "summary_tree"}
            

class Gff3( Gff ):
    """Tab delimited data in Gff3 format"""
    file_ext = "gff3"
    valid_gff3_strand = ['+', '-', '.', '?']
    valid_gff3_phase = ['.', '0', '1', '2']
    column_names = [ 'Seqid', 'Source', 'Type', 'Start', 'End', 'Score', 'Strand', 'Phase', 'Attributes' ]
        
    """Add metadata elements"""
    MetadataElement( name="column_types", default=['str','str','str','int','int','float','str','int','list'], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False )
    
    def __init__(self, **kwd):
        """Initialize datatype, by adding GBrowse display app"""
        Gff.__init__(self, **kwd)
    def set_meta( self, dataset, overwrite = True, **kwd ):
        i = 0
        for i, line in enumerate( file ( dataset.file_name ) ):
            line = line.rstrip('\r\n')
            if line and not line.startswith( '#' ):
                elems = line.split( '\t' )
                valid_start = False
                valid_end = False
                if len( elems ) == 9:
                    try:
                        start = int( elems[3] )
                        valid_start = True                                    
                    except:
                        if elems[3] == '.':
                            valid_start = True                                        
                    try:
                        end = int( elems[4] )
                        valid_end = True
                    except:
                        if elems[4] == '.':
                            valid_end = True
                    strand = elems[6]
                    phase = elems[7]
                    if valid_start and valid_end and start < end and strand in self.valid_gff3_strand and phase in self.valid_gff3_phase:
                        break
        Tabular.set_meta( self, dataset, overwrite = overwrite, skip = i )
    def sniff( self, filename ):
        """
        Determines whether the file is in gff version 3 format
        
        GFF 3 format:
    
        1) adds a mechanism for representing more than one level 
           of hierarchical grouping of features and subfeatures.
        2) separates the ideas of group membership and feature name/id
        3) constrains the feature type field to be taken from a controlled
           vocabulary.
        4) allows a single feature, such as an exon, to belong to more than
           one group at a time.
        5) provides an explicit convention for pairwise alignments
        6) provides an explicit convention for features that occupy disjunct regions
        
        The format consists of 9 columns, separated by tabs (NOT spaces).
        
        Undefined fields are replaced with the "." character, as described in the original GFF spec.
    
        For complete details see http://song.sourceforge.net/gff3.shtml
        
        >>> fname = get_test_fname( 'test.gff' )
        >>> Gff3().sniff( fname )
        False
        >>> fname = get_test_fname('gff_version_3.gff')
        >>> Gff3().sniff( fname )
        True
        """
        headers = get_headers( filename, '\t' )
        try:
            if len(headers) < 2:
                return False
            for hdr in headers:
                if hdr and hdr[0].startswith( '##gff-version' ) and hdr[0].find( '3' ) >= 0:
                    return True
                elif hdr and hdr[0].startswith( '##gff-version' ) and hdr[0].find( '3' ) < 0:
                    return False
                # Header comments may have been stripped, so inspect the data
                if hdr and hdr[0] and not hdr[0].startswith( '#' ):
                    if len(hdr) != 9: 
                        return False
                    try:
                        int( hdr[3] )
                    except:
                        if hdr[3] != '.':
                            return False
                    try:
                        int( hdr[4] )
                    except:
                        if hdr[4] != '.':
                            return False
                    if hdr[5] != '.':
                        try:
                            score = float( hdr[5] )
                        except:
                            return False
                    if hdr[6] not in self.valid_gff3_strand:
                        return False
                    if hdr[7] not in self.valid_gff3_phase:
                        return False
            return True
        except:
            return False

class Gtf( Gff ):
    """Tab delimited data in Gtf format"""
    file_ext = "gtf"
    column_names = [ 'Seqname', 'Source', 'Feature', 'Start', 'End', 'Score', 'Strand', 'Frame', 'Attributes' ]
    
    """Add metadata elements"""
    MetadataElement( name="columns", default=9, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_types", default=['str','str','str','int','int','float','str','int','list'], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False )
    
    MetadataElement( name="attributes", default=0, desc="Number of attributes", readonly=True, visible=False, no_value=0 )
    MetadataElement( name="attribute_types", default={}, desc="Attribute types", param=metadata.DictParameter, readonly=True, visible=False, no_value=[] )
    
    def sniff( self, filename ):
        """
        Determines whether the file is in gtf format
        
        GTF lines have nine required fields that must be tab-separated. The first eight GTF fields are the same as GFF. 
        The group field has been expanded into a list of attributes. Each attribute consists of a type/value pair. 
        Attributes must end in a semi-colon, and be separated from any following attribute by exactly one space.
        The attribute list must begin with the two mandatory attributes:

            gene_id value - A globally unique identifier for the genomic source of the sequence.
            transcript_id value - A globally unique identifier for the predicted transcript.
        
        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format4
        
        >>> fname = get_test_fname( '1.bed' )
        >>> Gtf().sniff( fname )
        False
        >>> fname = get_test_fname( 'test.gff' )
        >>> Gtf().sniff( fname )
        False
        >>> fname = get_test_fname( 'test.gtf' )
        >>> Gtf().sniff( fname )
        True
        """
        headers = get_headers( filename, '\t' )
        try:
            if len(headers) < 2:
                return False
            for hdr in headers:
                if hdr and hdr[0].startswith( '##gff-version' ) and hdr[0].find( '2' ) < 0:
                    return False
                if hdr and hdr[0] and not hdr[0].startswith( '#' ):
                    if len(hdr) != 9:
                        return False
                    try:
                        int( hdr[3] )
                        int( hdr[4] )
                    except:
                        return False
                    if hdr[5] != '.':
                        try:
                            score = float( hdr[5] )
                        except:
                            return False
                    if hdr[6] not in data.valid_strand:
                        return False

                    # Check attributes for gene_id, transcript_id
                    attributes = parse_gff_attributes( hdr[8] )
                    if len( attributes ) >= 2:
                        if 'gene_id' not in attributes:
                            return False
                        if 'transcript_id' not in attributes:
                            return False
                    else:
                        return False
            return True
        except:
            return False
            
    def set_meta( self, dataset, overwrite = True, **kwd ):        
        # Use first N lines to set metadata for dataset attributes. Attributes 
        # not found in the first N lines will not have metadata.
        num_lines = 200
        attribute_types = {}
        for i, line in enumerate( file ( dataset.file_name ) ):
            if line and not line.startswith( '#' ):
                elems = line.split( '\t' )
                if len( elems ) == 9:
                    try:
                        # Loop through attributes to set types.
                        for name, value in parse_gff_attributes( elems[8] ).items():
                            # Default type is string.
                            value_type = "str"
                            try:
                                # Try int.
                                int( value )
                                value_type = "int"
                            except:
                                try: 
                                    # Try float.
                                    float( value )
                                    value_type = "float"
                                except:
                                    pass
                            attribute_types[ name ] = value_type
                    except:
                        pass
                if i + 1 == num_lines:
                    break
        
        # Set attribute metadata and then set additional metadata.
        dataset.metadata.attribute_types = attribute_types
        dataset.metadata.attributes = len( attribute_types )
        Gff.set_meta( self, dataset, overwrite = overwrite, skip = i )
        
    def get_track_type( self ):
        return "FeatureTrack", {"data": "tabix", "index": "summary_tree"}


class Wiggle( Tabular, _RemoteCallMixin ):
    """Tab delimited data in wiggle format"""
    file_ext = "wig"

    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )
    
    def __init__( self, **kwd ):
        Tabular.__init__( self, **kwd )
        self.add_display_app( 'ucsc', 'display at UCSC', 'as_ucsc_display_file', 'ucsc_links' )
        self.add_display_app( 'gbrowse', 'display in Gbrowse', 'as_gbrowse_display_file', 'gbrowse_links' )
    def get_estimated_display_viewport( self, dataset ):
        """Return a chrom, start, stop tuple for viewing a file."""
        viewport_feature_count = 100 # viewport should check at least 100 features; excludes comment lines
        max_line_count = max( viewport_feature_count, 500 ) # maximum number of lines to check; includes comment lines
        if self.displayable( dataset ):
            try:
                chrom = None 
                start = sys.maxint 
                end = 0
                span = 1
                step = None
                fh = open( dataset.file_name )
                while True:
                    line = fh.readline( VIEWPORT_READLINE_BUFFER_SIZE )
                    if not line: break #EOF
                    try:
                        if line.startswith( "browser" ):
                            chr_info = line.rstrip( '\n\r' ).split()[-1]
                            chrom, coords = chr_info.split( ":" )
                            start, end = map( int, coords.split( "-" ) )
                            break # use the browser line
                        # variableStep chrom=chr20
                        if line and ( line.lower().startswith( "variablestep" ) or line.lower().startswith( "fixedstep" ) ):
                            if chrom is not None: break #different chrom or different section of the chrom
                            chrom = line.rstrip( '\n\r' ).split("chrom=")[1].split()[0]
                            if 'span=' in line:
                                span = int( line.rstrip( '\n\r' ).split("span=")[1].split()[0] )
                            if 'step=' in line:
                                step = int( line.rstrip( '\n\r' ).split("step=")[1].split()[0] )
                                start = int( line.rstrip( '\n\r' ).split("start=")[1].split()[0] )
                        else:
                            fields = line.rstrip( '\n\r' ).split()
                            if fields:
                                if step is not None:
                                    if not end:
                                        end = start + span
                                    else:
                                        end += step
                                else:
                                    start = min( int( fields[0] ), start )
                                    end = max( end, int( fields[0] ) + span )
                                viewport_feature_count -= 1
                    except:
                        pass
                    #make sure we are at the next new line
                    readline_count = VIEWPORT_MAX_READS_PER_LINE
                    while line.rstrip( '\n\r' ) == line:
                        assert readline_count > 0, Exception( 'Viewport readline count exceeded for dataset %s.' % dataset.id )
                        line = fh.readline( VIEWPORT_READLINE_BUFFER_SIZE )
                        if not line: break #EOF
                        readline_count -= 1
                    max_line_count -= 1
                    if not viewport_feature_count or not max_line_count:
                        #exceeded viewport or total line count to check
                        break
                if chrom is not None:
                    return ( chrom, str( start ), str( end ) ) #Necessary to return strings?
            except Exception, e:
                #unexpected error
                log.exception( str( e ) )
        return ( None, None, None ) #could not determine viewport
    def gbrowse_links( self, dataset, type, app, base_url ):
        ret_val = []
        chrom, start, stop = self.get_estimated_display_viewport( dataset )
        if chrom is not None:
            for site_name, site_url in util.get_gbrowse_sites_by_build( dataset.dbkey ):
                if site_name in app.config.gbrowse_display_sites:
                    if chrom.startswith( 'chr' ) and len ( chrom ) > 3:
                        chrom = chrom[3:]
                    redirect_url = urllib.quote_plus( "%s/?q=%s:%s..%s&eurl=%%s" % ( site_url, chrom, start, stop ) )
                    link = self._get_remote_call_url( redirect_url, site_name, dataset, type, app, base_url )
                    ret_val.append( ( site_name, link ) )
        return ret_val
    def ucsc_links( self, dataset, type, app, base_url ):
        ret_val = []
        chrom, start, stop = self.get_estimated_display_viewport( dataset )
        if chrom is not None:
            for site_name, site_url in util.get_ucsc_by_build( dataset.dbkey ):
                if site_name in app.config.ucsc_display_sites:
                    redirect_url = urllib.quote_plus( "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s" % ( site_url, dataset.dbkey, chrom, start, stop ) )
                    link = self._get_remote_call_url( redirect_url, site_name, dataset, type, app, base_url )
                    ret_val.append( ( site_name, link ) )
        return ret_val
    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return Tabular.make_html_table( self, dataset, skipchars=['track', '#'] )
    def set_meta( self, dataset, overwrite = True, **kwd ):
        max_data_lines = None
        i = 0
        for i, line in enumerate( file ( dataset.file_name ) ):
            line = line.rstrip('\r\n')
            if line and not line.startswith( '#' ):
                elems = line.split( '\t' )
                try:
                    float( elems[0] ) #"Wiggle track data values can be integer or real, positive or negative values"
                    break
                except:
                    do_break = False
                    for col_startswith in data.col1_startswith:
                        if elems[0].lower().startswith( col_startswith ):
                            do_break = True
                            break
                    if do_break:
                        break
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            #we'll arbitrarily only use the first 100 data lines in this wig file to calculate tabular attributes (column types)
            #this should be sufficient, except when we have mixed wig track types (bed, variable, fixed), 
            #    but those cases are not a single table that would have consistant column definitions
            #optional metadata values set in Tabular class will be 'None'
            max_data_lines = 100
        Tabular.set_meta( self, dataset, overwrite = overwrite, skip = i, max_data_lines = max_data_lines )
    def sniff( self, filename ):
        """
        Determines wether the file is in wiggle format
    
        The .wig format is line-oriented. Wiggle data is preceeded by a track definition line,
        which adds a number of options for controlling the default display of this track.
        Following the track definition line is the track data, which can be entered in several
        different formats.
    
        The track definition line begins with the word 'track' followed by the track type.
        The track type with version is REQUIRED, and it currently must be wiggle_0.  For example,
        track type=wiggle_0...
        
        For complete details see http://genome.ucsc.edu/goldenPath/help/wiggle.html
        
        >>> fname = get_test_fname( 'interval1.bed' )
        >>> Wiggle().sniff( fname )
        False
        >>> fname = get_test_fname( 'wiggle.wig' )
        >>> Wiggle().sniff( fname )
        True
        """
        headers = get_headers( filename, None )
        try:
            for hdr in headers:
                if len(hdr) > 1 and hdr[0] == 'track' and hdr[1].startswith('type=wiggle'):
                    return True
            return False
        except:
            return False
    def get_track_window(self, dataset, data, start, end):
        """
        Assumes we have a numpy file.
        """
        # Maybe if we import here people will still be able to use Galaxy when numpy kills it
        pkg_resources.require("numpy>=1.2.1")
        #from numpy.lib import format
        import numpy

        range = end - start
        # Determine appropriate resolution to plot ~1000 points
        resolution = ( 10 ** math.ceil( math.log10( range / 1000 ) ) )
        # Restrict to valid range
        resolution = min( resolution, 100000 )
        resolution = max( resolution, 1 )
        # Memory map the array (don't load all the data)
        data = numpy.load( data )
        # Grab just what we need
        t_start = math.floor( start / resolution )
        t_end = math.ceil( end / resolution )
        x = numpy.arange( t_start, t_end ) * resolution
        y = data[ t_start : t_end ]
    
        return zip(x.tolist(), y.tolist())
    def get_track_resolution( self, dataset, start, end):
        range = end - start
        # Determine appropriate resolution to plot ~1000 points
        resolution = math.ceil( 10 ** math.ceil( math.log10( range / 1000 ) ) )
        # Restrict to valid range
        resolution = min( resolution, 100000 )
        resolution = max( resolution, 1 )
        return resolution
    def get_track_type( self ):
        return "LineTrack", {"data": "bigwig", "index": "bigwig"}

class CustomTrack ( Tabular ):
    """UCSC CustomTrack"""
    file_ext = "customtrack"

    def __init__(self, **kwd):
        """Initialize interval datatype, by adding UCSC display app"""
        Tabular.__init__(self, **kwd)
        self.add_display_app ( 'ucsc', 'display at UCSC', 'as_ucsc_display_file', 'ucsc_links' )
    def set_meta( self, dataset, overwrite = True, **kwd ):
        Tabular.set_meta( self, dataset, overwrite = overwrite, skip = 1 )
    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return Tabular.make_html_table( self, dataset, skipchars=['track', '#'] )
    def get_estimated_display_viewport( self, dataset, chrom_col = None, start_col = None, end_col = None ):
        """Return a chrom, start, stop tuple for viewing a file."""
        #FIXME: only BED and WIG custom tracks are currently supported
        #As per previously existing behavior, viewport will only be over the first intervals 
        max_line_count = 100 # maximum number of lines to check; includes comment lines
        variable_step_wig = False
        chrom = None
        span = 1
        if self.displayable( dataset ):
            try:
                fh = open( dataset.file_name )
                while True:
                    line = fh.readline( VIEWPORT_READLINE_BUFFER_SIZE )
                    if not line: break #EOF
                    if not line.startswith( '#' ):
                        try:
                            if variable_step_wig:
                                fields = line.rstrip().split()
                                if len( fields ) == 2:
                                    start = int( fields[ 0 ] )
                                    return ( chrom, str( start ), str( start + span ) )
                            elif line and ( line.lower().startswith( "variablestep" ) or line.lower().startswith( "fixedstep" ) ):
                                chrom = line.rstrip( '\n\r' ).split("chrom=")[1].split()[0]
                                if 'span=' in line:
                                    span = int( line.rstrip( '\n\r' ).split("span=")[1].split()[0] )
                                if 'start=' in line:
                                    start = int( line.rstrip( '\n\r' ).split("start=")[1].split()[0] )
                                    return ( chrom, str( start ), str( start + span )  )
                                else:
                                    variable_step_wig = True 
                            else:
                                fields = line.rstrip().split( '\t' )
                                if len( fields ) >= 3:
                                    chrom = fields[ 0 ]
                                    start = int( fields[ 1 ] )
                                    end = int( fields[ 2 ] )
                                    return ( chrom, str( start ), str( end ) )
                        except Exception:
                            #most likely a non-integer field has been encountered for start / stop
                            continue
                    #make sure we are at the next new line
                    readline_count = VIEWPORT_MAX_READS_PER_LINE
                    while line.rstrip( '\n\r' ) == line:
                        assert readline_count > 0, Exception( 'Viewport readline count exceeded for dataset %s.' % dataset.id )
                        line = fh.readline( VIEWPORT_READLINE_BUFFER_SIZE )
                        if not line: break #EOF
                        readline_count -= 1
                    max_line_count -= 1
                    if not max_line_count:
                        #exceeded viewport or total line count to check
                        break
            except Exception, e:
                #unexpected error
                log.exception( str( e ) )
        return ( None, None, None ) #could not determine viewport
    def ucsc_links( self, dataset, type, app, base_url ):
        ret_val = []
        chrom, start, stop = self.get_estimated_display_viewport(dataset)
        if chrom is not None:
            for site_name, site_url in util.get_ucsc_by_build(dataset.dbkey):
                if site_name in app.config.ucsc_display_sites:
                    internal_url = "%s" % url_for( controller='dataset', dataset_id=dataset.id, action='display_at', filename='ucsc_' + site_name )
                    display_url = urllib.quote_plus( "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at" % (base_url, url_for( controller='root' ), dataset.id, type) )
                    redirect_url = urllib.quote_plus( "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s" % (site_url, dataset.dbkey, chrom, start, stop ) )
                    link = '%s?redirect_url=%s&display_url=%s' % ( internal_url, redirect_url, display_url )
                    ret_val.append( (site_name, link) )
        return ret_val
    def sniff( self, filename ):
        """
        Determines whether the file is in customtrack format.
        
        CustomTrack files are built within Galaxy and are basically bed or interval files with the first line looking
        something like this.
        
        track name="User Track" description="User Supplied Track (from Galaxy)" color=0,0,0 visibility=1
        
        >>> fname = get_test_fname( 'complete.bed' )
        >>> CustomTrack().sniff( fname )
        False
        >>> fname = get_test_fname( 'ucsc.customtrack' )
        >>> CustomTrack().sniff( fname )
        True
        """
        headers = get_headers( filename, None )
        first_line = True
        for hdr in headers:
            if first_line:
                first_line = False
                try:
                    if hdr[0].startswith('track'):
                        color_found = False
                        visibility_found = False
                        for elem in hdr[1:]:
                            if elem.startswith('color'): color_found = True
                            if elem.startswith('visibility'): visibility_found = True
                            if color_found and visibility_found: break
                        if not color_found or not visibility_found: return False
                    else: return False
                except: return False
            else:     
                try:
                    if hdr[0] and not hdr[0].startswith( '#' ):
                        if len( hdr ) < 3: 
                            return False
                        try:
                            int( hdr[1] )
                            int( hdr[2] )
                        except: 
                            return False
                except: 
                    return False
        return True
        
class ENCODEPeak( Interval ):
    '''
    Human ENCODE peak format. There are both broad and narrow peak formats. 
    Formats are very similar; narrow peak has an additional column, though.
    
    Broad peak ( http://genome.ucsc.edu/FAQ/FAQformat#format13 ):
    This format is used to provide called regions of signal enrichment based 
    on pooled, normalized (interpreted) data. It is a BED 6+3 format.
    
    Narrow peak http://genome.ucsc.edu/FAQ/FAQformat#format12 and :
    This format is used to provide called peaks of signal enrichment based on
    pooled, normalized (interpreted) data. It is a BED6+4 format.
    '''
    
    file_ext = "encodepeak"
    column_names = [ 'Chrom', 'Start', 'End', 'Name', 'Score', 'Strand', 'SignalValue', 'pValue', 'qValue', 'Peak' ]
    
    """Add metadata elements"""
    MetadataElement( name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter )
    MetadataElement( name="endCol", default=3, desc="End column", param=metadata.ColumnParameter )
    MetadataElement( name="strandCol", desc="Strand column (click box & select)", param=metadata.ColumnParameter, optional=True, no_value=0 )
    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )
    
    def sniff( self, filename ):
        return False
        
    def get_track_type( self ):
        return "FeatureTrack", {"data": "tabix", "index": "summary_tree"}    

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
