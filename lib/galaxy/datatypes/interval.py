"""
Interval datatypes

"""
import pkg_resources
pkg_resources.require( "bx-python" )

import logging, os, sys, time, tempfile, shutil
import data
from galaxy import util
from galaxy.datatypes.sniff import *
from galaxy.web import url_for
from cgi import escape
import urllib
from bx.intervals.io import *
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.tabular import Tabular
import math

log = logging.getLogger(__name__)

#
# contain the meta columns and the words that map to it
# list aliases on the right side of the : in decreasing order of priority
#
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

class Interval( Tabular ):
    """Tab delimited data containing interval information"""
    file_ext = "interval"

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
    
    def set_peek( self, dataset, line_count=None, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            if line_count is None:
                # See if line_count is stored in the metadata
                if dataset.metadata.data_lines:
                    dataset.blurb = "%s regions" % util.commaify( str( dataset.metadata.data_lines ) )
                else:
                    # Number of lines is not known ( this should not happen ), and auto-detect is
                    # needed to set metadata
                    dataset.blurb = "? regions"
            else:
                dataset.blurb = "%s regions" % util.commaify( str( line_count ) )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def set_meta( self, dataset, overwrite = True, first_line_is_header = False, **kwd ):
        Tabular.set_meta( self, dataset, overwrite = overwrite, skip = 0 )
        
        """Tries to guess from the line the location number of the column for the chromosome, region start-end and strand"""
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
                        valid = dict( alias_helper ) # shrinks
                        for index, col_name in enumerate( elems ):
                            if col_name in valid:
                                meta_name = valid[col_name]
                                if overwrite or not dataset.metadata.element_is_set( meta_name ):
                                    setattr( dataset.metadata, meta_name, index+1 )
                                values = alias_spec[ meta_name ]
                                start = values.index( col_name )
                                for lower in values[ start: ]:
                                    del valid[ lower ]  # removes lower priority keys 
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
    
    def get_estimated_display_viewport( self, dataset ):
        """Return a chrom, start, stop tuple for viewing a file."""
        if dataset.has_data() and dataset.state == dataset.states.OK:
            try:
                c, s, e = dataset.metadata.chromCol, dataset.metadata.startCol, dataset.metadata.endCol
                c, s, e = int(c)-1, int(s)-1, int(e)-1
                
                peek = []
                for idx, line in enumerate(file(dataset.file_name)):
                    if line[0] != '#':
                        peek.append( line.split() )
                        if idx > 10:
                            break

                chr, start, stop = peek[0][c], int( peek[0][s] ), int( peek[0][e] )
                
                for p in peek[1:]:
                    if p[0] == chr:
                        start = min( start, int( p[s] ) )
                        stop  = max( stop, int( p[e] ) )
            except Exception, exc:
                #log.error( 'Viewport generation error -> %s ' % str(exc) )
                (chr, start, stop) = 'chr1', 1, 1000
            return (chr, str( start ), str( stop )) 
        else:
            return ('', '', '')

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

    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        comments = []
        try:
            # Generate column header
            out.append('<tr>')
            for i in range( 1, dataset.metadata.columns+1 ):
                if i == dataset.metadata.chromCol:
                    out.append( '<th>%s.Chrom</th>' % i )
                elif i == dataset.metadata.startCol:
                    out.append( '<th>%s.Start</th>' % i )
                elif i == dataset.metadata.endCol:
                    out.append( '<th>%s.End</th>' % i )
                elif dataset.metadata.strandCol and i == dataset.metadata.strandCol:
                    out.append( '<th>%s.Strand</th>' % i )
                elif dataset.metadata.nameCol and i == dataset.metadata.nameCol:
                    out.append( '<th>%s.Name</th>' % i )
                else:
                    out.append( '<th>%s</th>' % i )
            out.append('</tr>')
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % str( exc )
        return out

    def ucsc_links( self, dataset, type, app, base_url ):
        ret_val = []
        if dataset.has_data:
            viewport_tuple = self.get_estimated_display_viewport(dataset)
            if viewport_tuple:
                chrom = viewport_tuple[0]
                start = viewport_tuple[1]
                stop = viewport_tuple[2]
                for site_name, site_url in util.get_ucsc_by_build(dataset.dbkey):
                    if site_name in app.config.ucsc_display_sites:
                        # HACK: UCSC doesn't support https, so force http even
                        # if our URL scheme is https.  Making this work
                        # requires additional hackery in your upstream proxy.
                        # If UCSC ever supports https, remove this hack.
                        internal_url = "%s" % url_for( controller='dataset', dataset_id=dataset.id, action='display_at', filename='ucsc_' + site_name )
                        if base_url.startswith( 'https://' ):
                            base_url = base_url.replace( 'https', 'http', 1 )
                        display_url = urllib.quote_plus( "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at" % (base_url, url_for( controller='root' ), dataset.id, type) )
                        redirect_url = urllib.quote_plus( "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s" % (site_url, dataset.dbkey, chrom, start, stop ) )
                        link = '%s?redirect_url=%s&display_url=%s' % ( internal_url, redirect_url, display_url )
                        ret_val.append( (site_name, link) )
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
        return "FeatureTrack"
    
class Bed( Interval ):
    """Tab delimited data in BED format"""
    file_ext = "bed"

    """Add metadata elements"""
    MetadataElement( name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter )
    MetadataElement( name="endCol", default=3, desc="End column", param=metadata.ColumnParameter )
    MetadataElement( name="strandCol", desc="Strand column (click box & select)", param=metadata.ColumnParameter, optional=True, no_value=0 )
    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )
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

class _RemoteCallMixin:
    def _get_remote_call_url( self, redirect_url, site_name, dataset, type, app, base_url ):
        """Retrieve the URL to call out to an external site and retrieve data.
        This routes our external URL through a local galaxy instance which makes
        the data available, followed by redirecting to the remote site with a
        link back to the available information.
        """
        internal_url = "%s" % url_for( controller='dataset', dataset_id=dataset.id, action='display_at', filename='%s_%s' % ( type, site_name ) )
        base_url = app.config.get( "display_at_callback", base_url )
        if base_url.startswith( 'https://' ):
            base_url = base_url.replace( 'https', 'http', 1 )
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
        self.add_display_app( 'c_elegans', 'display in Wormbase', 'as_gbrowse_display_file', 'gbrowse_links' )
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
    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        comments = []
        try:
            # Generate column header
            out.append( '<tr>' )
            for i, name in enumerate( self.column_names ):
                out.append( '<th>%s.%s</th>' % ( str( i+1 ), name ) )
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % exc
        return out
    def get_estimated_display_viewport( self, dataset ):
        """
        Return a chrom, start, stop tuple for viewing a file.  There are slight differences between gff 2 and gff 3
        formats.  This function should correctly handle both...
        """
        if dataset.has_data() and dataset.state == dataset.states.OK:
            try:
                seqid = ''
                start = 2147483647  # Maximum value of a signed 32 bit integer ( 2**31 - 1 )
                stop = 0
                for i, line in enumerate( file( dataset.file_name ) ):
                    line = line.rstrip( '\r\n' )
                    if not line:
                        continue
                    if line.startswith( '##sequence-region' ): # ##sequence-region IV 6000000 6030000
                        elems = line.split()
                        seqid = elems[1] # IV
                        start = elems[2] # 6000000
                        stop = elems[3] # 6030000
                        break
                    # Allow UCSC style browser and track info in the GFF file
                    if line.startswith("browser position"):
                        pos_info = line.split()[-1]
                        seqid, startend = pos_info.split(":")
                        start, end = startend.split("-")
                        break
                    if not line.startswith(('#', 'track', 'browser')) :
                        elems = line.split( '\t' )
                        if not seqid:
                            # We can only set the viewport for a single chromosome
                            seqid = elems[0]
                        if seqid == elems[0]:
                            # Make sure we have not spanned chromosomes
                            start = min( start, int( elems[3] ) )
                            stop = max( stop, int( elems[4] ) )
                        else:
                            # We've spanned a chromosome
                            break
                    if i > 10:
                        break
            except:
                seqid, start, stop = ( '', '', '' ) 
            return ( seqid, str( start ), str( stop ) )
        else:
            return ( '', '', '' )
    def ucsc_links( self, dataset, type, app, base_url ):
        ret_val = []
        if dataset.has_data:
            seqid, start, stop = self.get_estimated_display_viewport( dataset )
            if seqid and start and stop:
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
        if dataset.has_data:
            viewport_tuple = self.get_estimated_display_viewport( dataset )
            seqid = viewport_tuple[0]
            start = viewport_tuple[1]
            stop = viewport_tuple[2]
            if seqid and start and stop:
                for site_name, site_url in util.get_gbrowse_sites_by_build( dataset.dbkey ):
                    if site_name in app.config.gbrowse_display_sites:
                        redirect_url = urllib.quote_plus( "%s%s/?ref=%s&start=%s&stop=%s&eurl=%%s" % 
                                ( site_url, dataset.dbkey, seqid, start, stop ) )
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
                            score = int(hdr[5])
                        except:
                            return False
                        if (score < 0 or score > 1000):
                            return False
                    if hdr[6] not in data.valid_strand:
                        return False
            return True
        except:
            return False

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
                            score = int(hdr[5])
                        except:
                            return False
                        if (score < 0 or score > 1000):
                            return False
                    if hdr[6] not in self.valid_gff3_strand:
                        return False
                    if hdr[7] not in self.valid_gff3_phase:
                        return False
            return True
        except:
            return False

class Wiggle( Tabular, _RemoteCallMixin ):
    """Tab delimited data in wiggle format"""
    file_ext = "wig"

    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )
    
    def __init__( self, **kwd ):
        Tabular.__init__( self, **kwd )
        self.add_display_app( 'ucsc', 'display at UCSC', 'as_ucsc_display_file', 'ucsc_links' )
        self.add_display_app( 'gbrowse', 'display in Gbrowse', 'as_gbrowse_display_file', 'gbrowse_links' )
    def get_estimated_display_viewport( self, dataset ):
        value = ( "", "", "" )
        num_check_lines = 100 # only check up to this many non empty lines
        for i, line in enumerate( file( dataset.file_name ) ):
            line = line.rstrip( '\r\n' )
            if line and line.startswith( "browser" ):
                chr_info = line.split()[-1]
                wig_chr, coords = chr_info.split( ":" )
                start, end = coords.split( "-" )
                value = ( wig_chr, start, end )
                break
            if i > num_check_lines:
                break
        return value
    def _get_viewer_range( self, dataset ):
        """Retrieve the chromosome, start, end for an external viewer."""
        if dataset.has_data:
            viewport_tuple = self.get_estimated_display_viewport( dataset )
            if viewport_tuple:
                chrom = viewport_tuple[0]
                start = viewport_tuple[1]
                stop = viewport_tuple[2]
                return ( chrom, start, stop )
        return ( None, None, None )
    def gbrowse_links( self, dataset, type, app, base_url ):
        ret_val = []
        chrom, start, stop = self._get_viewer_range( dataset )
        if chrom is not None:
            for site_name, site_url in util.get_gbrowse_sites_by_build( dataset.dbkey ):
                if site_name in app.config.gbrowse_display_sites:
                    redirect_url = urllib.quote_plus( "%s%s/?ref=%s&start=%s&stop=%s&eurl=%%s" % ( site_url, dataset.dbkey, chrom, start, stop ) )
                    link = self._get_remote_call_url( redirect_url, site_name, dataset, type, app, base_url )
                    ret_val.append( ( site_name, link ) )
        return ret_val
    def ucsc_links( self, dataset, type, app, base_url ):
        ret_val = []
        chrom, start, stop = self._get_viewer_range( dataset )
        if chrom is not None:
            for site_name, site_url in util.get_ucsc_by_build( dataset.dbkey ):
                if site_name in app.config.ucsc_display_sites:
                    redirect_url = urllib.quote_plus( "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s" % ( site_url, dataset.dbkey, chrom, start, stop ) )
                    link = self._get_remote_call_url( redirect_url, site_name, dataset, type, app, base_url )
                    ret_val.append( ( site_name, link ) )
        return ret_val
    def make_html_table( self, dataset ):
        return Tabular.make_html_table( self, dataset, skipchars=['track', '#'] )
    def set_meta( self, dataset, overwrite = True, **kwd ):
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
                    for str in data.col1_startswith:
                        if elems[0].lower().startswith(str):
                            do_break = True
                            break
                    if do_break:
                        break
        Tabular.set_meta( self, dataset, overwrite = overwrite, skip = i )
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
        return "LineTrack"

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
    def get_estimated_display_viewport( self, dataset ):
        try:
            wiggle_format = False
            for line in open(dataset.file_name):
                if (line.startswith("chr") or line.startswith("scaffold")):  
                    start = line.split("\t")[1].replace(",","")   
                    end = line.split("\t")[2].replace(",","")

                    if int(start) < int(end):
                        value = ( line.split("\t")[0], start, end )
                    else:
                        value = ( line.split("\t")[0], end, start )

                    break

                elif (line.startswith('variableStep')):
                    # wiggle format
                    wiggle_format = True
                    wig_chr = line.split()[1].split('=')[1]
                    if not wig_chr.startswith("chr"):
                        value = ('', '', '')
                        break
                elif wiggle_format:
                    # wiggle format
                    if line.split("\t")[0].isdigit():
                        start = line.split("\t")[0]
                        end = str(int(start) + 1)
                        value = (wig_chr, start, end)
                    else:
                        value = (wig_chr, '', '')
                    break
                            
            return value #returns the co-ordinates of the 1st track/dataset
        except:
            #return "."
            return ('', '', '')
    def ucsc_links( self, dataset, type, app, base_url ):
        ret_val = []
        if dataset.has_data:
            viewport_tuple = self.get_estimated_display_viewport(dataset)
            if viewport_tuple:
                chrom = viewport_tuple[0]
                start = viewport_tuple[1]
                stop = viewport_tuple[2]
                for site_name, site_url in util.get_ucsc_by_build(dataset.dbkey):
                    if site_name in app.config.ucsc_display_sites:
                        internal_url = "%s" % url_for( controller='dataset', dataset_id=dataset.id, action='display_at', filename='ucsc_' + site_name )
                        if base_url.startswith( 'https://' ):
                            base_url = base_url.replace( 'https', 'http', 1 )
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

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
