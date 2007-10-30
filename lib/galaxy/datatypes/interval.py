"""
Interval datatypes

"""
import pkg_resources
pkg_resources.require( "bx-python" )

import logging, os, sys, time, sets, tempfile, shutil
import data
from galaxy import util
from galaxy.datatypes.sniff import *
from cgi import escape
import urllib
from bx.intervals.io import *
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.tabular import Tabular

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
    MetadataElement( name="chromCol", desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="startCol", desc="Start column", param=metadata.ColumnParameter )
    MetadataElement( name="endCol", desc="End column", param=metadata.ColumnParameter )
    MetadataElement( name="strandCol", desc="Strand column (click box & select)", param=metadata.ColumnParameter, optional=True, no_value=0 )
    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )

    def __init__(self, **kwd):
        """Initialize interval datatype, by adding UCSC display apps"""
        Tabular.__init__(self, **kwd)
        self.add_display_app ( 'ucsc', 'display at UCSC', 'as_ucsc_display_file', 'ucsc_links' )
    
    def missing_meta( self, dataset ):
        """Checks for empty meta values"""
        for key, value in dataset.metadata.items():
            if key in ['strandCol']: continue #we skip check for strand column here, since it is considered optional
            if not value:
                return True
        return False
    
    def init_meta( self, dataset, copy_from=None ):
        Tabular.init_meta( self, dataset, copy_from=copy_from )
    
    def set_peek( self, dataset ):
        """Set the peek and blurb text"""
        dataset.peek  = data.get_file_peek( dataset.file_name )
        ## dataset.peek  = self.make_html_table( dataset.peek )
        dataset.blurb = util.commaify( str( data.get_line_count( dataset.file_name ) ) ) + " regions"
        #i don't think set_meta should not be called here, it should be called separately
        #self.set_meta( dataset )
    
    def set_meta( self, dataset, first_line_is_header=False ):
        Tabular.set_meta( self, dataset, 1 )
        
        """Tries to guess from the line the location number of the column for the chromosome, region start-end and strand"""
        if dataset.has_data():
            for i, line in enumerate( file(dataset.file_name) ):
                line = line.rstrip('\r\n')
                if len(line)>0:
                    if (first_line_is_header or line[0] == '#'):
                        self.init_meta(dataset)
                        line  = line.strip("#")
                        elems = line.split("\t")
                        valid = dict(alias_helper) # shrinks
                        for index, col_name in enumerate(elems):
                            if col_name in valid:
                                meta_name = valid[col_name]
                                setattr(dataset.metadata, meta_name, index+1)
                                values = alias_spec[meta_name]
                                start  = values.index(col_name)
                                for lower in values[start:]:
                                    del valid[lower]  # removes lower priority keys 
                        break  # Our metadata is set, so break out of the outer loop
    
    def get_estimated_display_viewport( self, dataset ):
        """Return a chrom, start, stop tuple for viewing a file."""
        if dataset.has_data() and dataset.state == dataset.states.OK:
            try:
                c, s, e, t = dataset.metadata.chromCol, dataset.metadata.startCol, dataset.metadata.endCol, dataset.metadata.strandCol 
                c, s, e, t = int(c)-1, int(s)-1, int(e)-1, int(t)-1
                
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
        c, s, e, t = dataset.metadata.chromCol, dataset.metadata.startCol, dataset.metadata.endCol, dataset.metadata.strandCol 
        c, s, e, t = int(c)-1, int(s)-1, int(e)-1, int(t)-1
        if t >= 0: # strand column (should) exists
            for elems in util.file_iter(dataset.file_name):
                strand = "+"
                if t<len(elems): strand = elems[t]
                tmp = [ elems[c], elems[s], elems[e], '1', '2', strand ]
                os.write(fd, '%s\n' % '\t'.join(tmp) )
        else:
            for elems in util.file_iter(dataset.file_name):
                tmp = [ elems[c], elems[s], elems[e] ]
                os.write(fd, '%s\n' % '\t'.join(tmp) )    
        os.close(fd)
        return open(temp_name)

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
                        display_url = urllib.quote_plus( "%s/display_as?id=%i&display_app=%s" % (base_url, dataset.id, type) )
                        link = "%sdb=%s&position=%s:%s-%s&hgt.customText=%s" % (site_url, dataset.dbkey, chrom, start, stop, display_url )
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
                if not (hdr[0] == '' or hdr[0].startswith( '#' )):
                    if len(hdr) < 3:
                        return False
                    try:
                        map( int, [hdr[1], hdr[2]] )
                    except:
                        return False
            return True
        except:
            return False
    
class Bed( Interval ):
    """Tab delimited data in BED format"""
    file_ext = "bed"

    """Add metadata elements"""
    MetadataElement( name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter )
    MetadataElement( name="endCol", default=3, desc="End column", param=metadata.ColumnParameter )
    MetadataElement( name="strandCol", desc="Strand column (click box & select)", param=metadata.ColumnParameter, optional=True, no_value=0 )
    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )
    
    def missing_meta( self, dataset ):
        """Checks for empty meta values"""
        return Tabular.missing_meta(self, dataset)
    
    def init_meta( self, dataset, copy_from=None ):
        Interval.init_meta( self, dataset, copy_from=copy_from )
    
    def set_meta( self, dataset ):
        """Sets the metadata information for datasets previously determined to be in bed format."""
        i = 0
        if dataset.has_data():
            for i, line in enumerate( file(dataset.file_name) ):
                line = line.rstrip('\r\n')
                if line and not line.startswith('#'):
                    elems = line.split('\t')
                    if len(elems) > 2:
                        for str in data.col1_startswith:
                            if line.lower().startswith(str):
                                if len(elems) < 6:
                                    dataset.metadata.strandCol = 0
                                else:
                                    dataset.metadata.strandCol = 6
                                break
            Tabular.set_meta( self, dataset, i )
    
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
                    try: map( int, [hdr[1], hdr[2]] )
                    except: return False
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

class Gff( Tabular ):
    """Tab delimited data in Gff format"""
    file_ext = "gff"

    """Add metadata elements"""
    MetadataElement( name="columns", default=9, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_types", default=['str','str','str','int','int','int','str','str','str'], desc="Column types", readonly=True, visible=False )
    
    def __init__(self, **kwd):
        """Initialize datatype, by adding GBrowse display app"""
        Tabular.__init__(self, **kwd)
        self.add_display_app ('gbrowse', 'display in GBrowse', 'as_gbrowse_display_file', 'gbrowse_links' )

    def set_meta( self, dataset ):
        i = 0
        for i, line in enumerate( file ( dataset.file_name ) ):
            line = line.rstrip('\r\n')
            if line and not line.startswith( '#' ):
                elems = line.split( '\t' )
                if len(elems) == 9:
                    try:
                        map( int, [elems[3], elems[4]] )
                        break
                    except: pass
        Tabular.set_meta( self, dataset, i )

    def make_html_table(self, data):
        return Tabular.make_html_table(self, data, skipchar='#')
    
    def as_gbrowse_display_file( self, dataset, **kwd ):
        """Returns file contents that can be displayed in GBrowse apps."""
        #TODO: fix me...
        return open(dataset.file_name)

    def get_estimated_display_viewport( self, dataset ):
        """
        Return a chrom, start, stop tuple for viewing a file.  There are slight differences between gff and gff version 3
        formats.  This function should correctly handle both...
        """
        if dataset.has_data() and dataset.state == dataset.states.OK:
            try:
                seqid_col = 0
                start_col = 3
                stop_col = 4
                
                peek = []
                for idx, line in enumerate(file(dataset.file_name)):
                    if line[0] != '#':
                        peek.append( line.split() )
                        if idx > 10:
                            break

                seqid, start, stop = peek[0][seqid_col], int( peek[0][start_col] ), int( peek[0][stop_col] )
                
                for p in peek[1:]:
                    if p[0] == seqid:
                        start = min( start, int( p[start_col] ) )
                        stop  = max( stop, int( p[stop_col] ) )
            except Exception, exc:
                #log.error( 'Viewport generation error -> %s ' % str(exc) )
                seqid, start, stop = ('', '', '') 
            return (seqid, str( start ), str( stop ))
        else:
            return ('', '', '')

    def gbrowse_links( self, dataset, type, app, base_url ):
        ret_val = []
        if dataset.has_data:
            viewport_tuple = self.get_estimated_display_viewport(dataset)
            if viewport_tuple:
                chrom = viewport_tuple[0]
                start = viewport_tuple[1]
                stop = viewport_tuple[2]
                for site_name, site_url in util.get_gbrowse_sites_by_build(dataset.dbkey):
                    if site_name in app.config.gbrowse_display_sites:
                        display_url = urllib.quote_plus( "%s/display_as?id=%i&display_app=%s" % (base_url, dataset.id, type) )
                        link = "%sname=%s&ref=%s:%s..%s&eurl=%s" % (site_url, dataset.dbkey, chrom, start, stop, display_url )                        
                        ret_val.append( (site_name, link) )
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
                        map( int, [hdr[3], hdr[4]] )
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
        
    """Add metadata elements"""
    MetadataElement( name="column_types", default=['str','str','str','int','int','float','str','int','list'], desc="Column types", readonly=True, visible=False )
    
    def __init__(self, **kwd):
        """Initialize datatype, by adding GBrowse display app"""
        Gff.__init__(self, **kwd)

    def set_meta( self, dataset ):
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
                        if elems[3] == '.': valid_start = True                                        
                    try:
                        end = int( elems[4] )
                        valid_end = True
                    except:
                        if elems[4] == '.': valid_end = True
                    strand = elems[6]
                    phase = elems[7]
                    if valid_start and valid_end and start < end and strand in self.valid_gff3_strand and phase in self.valid_gff3_phase:
                        break
        Tabular.set_meta( self, dataset, i )

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
                if hdr and hdr[0].startswith( '##gff-version' ) and hdr[0].find( '3' ) < 0:
                    return False
                if hdr and hdr[0] and not hdr[0].startswith( '#' ):
                    if len(hdr) != 9: 
                        return False
                    try:
                        map( int, [hdr[3]] )
                    except:
                        if hdr[3] != '.':
                            return False
                    try:
                        map( int, [hdr[4]] )
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

class Wiggle( Tabular ):
    """Tab delimited data in wiggle format"""
    file_ext = "wig"

    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True, visible=False )
    
    def make_html_table(self, data):
        return Tabular.make_html_table(self, data, skipchar='#')

    def set_meta( self, dataset ):
        i = 0
        for i, line in enumerate( file ( dataset.file_name ) ):
            line = line.rstrip('\r\n')
            if line and not line.startswith( '#' ):
                elems = line.split( '\t' )
                try:
                    int( elems[0] )
                    break
                except:
                    for str in data.col1_startswith:
                        if elems[0].lower().startswith(str):
                            break
        Tabular.set_meta( self, dataset, i )

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

class CustomTrack ( Tabular ):
    """UCSC CustomTrack"""
    file_ext = "customtrack"

    def __init__(self, **kwd):
        """Initialize interval datatype, by adding UCSC display app"""
        Tabular.__init__(self, **kwd)
        self.add_display_app ( 'ucsc', 'display at UCSC', 'as_ucsc_display_file', 'ucsc_links' )

    def set_meta( self, dataset ):
        Tabular.set_meta( self, dataset, 1 )

    def make_html_table(self, dataset):
        return Tabular.make_html_table(self, dataset, skipchar='track')

    def get_estimated_display_viewport( self, dataset ):
        try:
            for line in open(dataset.file_name):
                if (line.startswith("chr") or line.startswith("scaffold")):  
                    start = line.split("\t")[1].replace(",","")   
                    end = line.split("\t")[2].replace(",","")

                    if int(start) < int(end):
                        value = ( line.split("\t")[0], start, end )
                    else:
                        value = ( line.split("\t")[0], end, start )

                    break
            return value #returns the co-ordinates of the 1st track/dataset
        except:
            #return "."
            return ('', '', '')
    
    def as_ucsc_display_file( self, dataset ):
        return open(dataset.file_name)

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
                        display_url = urllib.quote_plus( "%s/display_as?id=%i&display_app=%s" % (base_url, dataset.id, type) )
                        link = "%sdb=%s&position=%s:%s-%s&hgt.customText=%s" % (site_url, dataset.dbkey, chrom, start, stop, display_url )
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
                try:
                    if hdr[0].startswith('track') and hdr[0].find('color') > -1 and hdr[0].find('visibility') > -1: first_line = False
                    else: return False
                except: return False
            else:     
                try:
                    if hdr[0] and not hdr[0].startswith( '#' ):
                        if len( hdr ) < 3: return False
                        try: map( int, [hdr[1], hdr[2]] )
                        except: return False
                except: return False
        return True

class GBrowseTrack ( Tabular ):
    """GMOD GBrowseTrack"""
    file_ext = "gbrowsetrack"

    def __init__(self, **kwd):
        """Initialize datatype, by adding GBrowse display app"""
        Tabular.__init__(self, **kwd)
        self.add_display_app ('gbrowse', 'display in GBrowse', 'as_gbrowse_display_file', 'gbrowse_links' )

    def set_meta( self, dataset ):
        Tabular.set_meta( self, dataset, 1 )
    
    def make_html_table(self, dataset):
        return Tabular.make_html_table(self, dataset, skipchar='track')
    
    def get_estimated_display_viewport( self, dataset ):
        #TODO: fix me...
        return ('', '', '')
    
    def gbrowse_links( self, dataset, type, app, base_url ):
        ret_val = []
        if dataset.has_data:
            viewport_tuple = self.get_estimated_display_viewport(dataset)
            if viewport_tuple:
                chrom = viewport_tuple[0]
                start = viewport_tuple[1]
                stop = viewport_tuple[2]
                for site_name, site_url in util.get_gbrowse_sites_by_build(dataset.dbkey):
                    if site_name in app.config.gbrowse_display_sites:
                        display_url = urllib.quote_plus( "%s/display_as?id=%i&display_app=%s" % (base_url, dataset.id, type) )
                        link = "%sname=%s&ref=%s:%s..%s&eurl=%s" % (site_url, dataset.dbkey, chrom, start, stop, display_url )                        
                        ret_val.append( (site_name, link) )
        return ret_val
        
    def as_gbrowse_display_file( self, dataset, **kwd ):
        """Returns file contents that can be displayed in GBrowse apps."""
        #TODO: fix me...
        return open(dataset.file_name)

    def sniff( self, filename ):
        """
        Determines whether the file is in gbrowsetrack format.
        
        GBrowseTrack files are built within Galaxy.
        TODO: Not yet sure what this file will look like.  Fix this sniffer and add some unit tests here as soon as we know.
        """
        return False

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
