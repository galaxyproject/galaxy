"""
Data providers for tracks visualizations.
"""

import sys
from math import ceil, log
import pkg_resources
pkg_resources.require( "bx-python" )
if sys.version_info[:2] == (2, 4):
    pkg_resources.require( "ctypes" )
pkg_resources.require( "pysam" )
pkg_resources.require( "numpy" )
import numpy
from galaxy.datatypes.util.gff_util import *
from galaxy.util.json import from_json_string
from bx.interval_index_file import Indexes
from bx.bbi.bigwig_file import BigWigFile
from galaxy.util.lrucache import LRUCache
from galaxy.visualization.tracks.summary import *
import galaxy_utils.sequence.vcf
from galaxy.datatypes.tabular import Vcf
from galaxy.datatypes.interval import Interval, Bed, Gff, Gtf, ENCODEPeak

from pysam import csamtools, ctabix

ERROR_MAX_VALS = "Only the first %i %s in this region are displayed."

# Return None instead of NaN to pass jQuery 1.4's strict JSON
def float_nan(n):
    if n != n: # NaN != NaN
        return None
    else:
        return float(n)
        
def get_bounds( reads, start_pos_index, end_pos_index ):
    """
    Returns the minimum and maximum position for a set of reads.
    """
    max_low = sys.maxint
    max_high = -sys.maxint
    for read in reads:
        if read[ start_pos_index ] < max_low:
            max_low = read[ start_pos_index ]
        if read[ end_pos_index ] > max_high:
            max_high = read[ end_pos_index ]
    return max_low, max_high
        
class TracksDataProvider( object ):
    """ Base class for tracks data providers. """
    
    """ 
    Mapping from column name to payload data; this mapping is used to create
    filters. Key is column name, value is a dict with mandatory key 'index' and 
    optional key 'name'. E.g. this defines column 4

    col_name_data_attr_mapping = {4 : { index: 5, name: 'Score' } }
    """
    col_name_data_attr_mapping = {}
    
    def __init__( self, converted_dataset=None, original_dataset=None, dependencies=None ):
        """ Create basic data provider. """
        self.converted_dataset = converted_dataset
        self.original_dataset = original_dataset
        self.dependencies = dependencies
        
    def write_data_to_file( self, chrom, start, end, filename ):
        """
        Write data in region defined by chrom, start, and end to a file.
        """
        raise Exception( "Unimplemented Function" )
        
    def valid_chroms( self ):
        """
        Returns chroms/contigs that the dataset contains
        """
        return None # by default
    
    def has_data( self, chrom, start, end, **kwargs ):
        """
        Returns true if dataset has data in the specified genome window, false
        otherwise.
        """
        raise Exception( "Unimplemented Function" )
        
    def get_iterator( self, chrom, start, end ):
        """
        Returns an iterator that provides data in the region chrom:start-end
        """
        raise Exception( "Unimplemented Function" )
        
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        """
        Process data from an iterator to a format that can be provided to client.
        """
        raise Exception( "Unimplemented Function" )        
        
    def get_data( self, chrom, start, end, start_val=0, max_vals=sys.maxint, **kwargs ):
        """ 
        Returns data in region defined by chrom, start, and end. start_val and
        max_vals are used to denote the data to return: start_val is the first element to 
        return and max_vals indicates the number of values to return.
        
        Return value must be a dictionary with the following attributes:
            dataset_type, data
        """
        iterator = self.get_iterator( chrom, start, end )
        return self.process_data( iterator, start_val, max_vals, **kwargs )
        
    def get_filters( self ):
        """ 
        Returns filters for provider's data. Return value is a list of 
        filters; each filter is a dictionary with the keys 'name', 'index', 'type'.
        NOTE: This method uses the original dataset's datatype and metadata to 
        create the filters.
        """
        # Get column names.
        try:
            column_names = self.original_dataset.datatype.column_names
        except AttributeError:
            try:
                column_names = range( self.original_dataset.metadata.columns )
            except: # Give up
                return []
            
        # Dataset must have column types; if not, cannot create filters.
        try:
            column_types = self.original_dataset.metadata.column_types
        except AttributeError:
            return []
            
        # Create and return filters.
        filters = []
        if self.original_dataset.metadata.viz_filter_cols:
            for viz_col_index in self.original_dataset.metadata.viz_filter_cols:
                # Some columns are optional, so can't assume that a filter 
                # column is in dataset.
                if viz_col_index >= len( column_names ):
                    continue;
                col_name = column_names[ viz_col_index ]
                # Make sure that column has a mapped index. If not, do not add filter.
                try:
                    attrs = self.col_name_data_attr_mapping[ col_name ]
                except KeyError:
                    continue
                filters.append(
                    { 'name' : attrs[ 'name' ], 'type' : column_types[viz_col_index], \
                    'index' : attrs[ 'index' ] } )
        return filters
        
#
# -- Base mixins and providers --
#

class FilterableMixin:
    def get_filters( self ):
        """ Returns a dataset's filters. """
        
        # is_ functions taken from Tabular.set_meta
        def is_int( column_text ):
            try:
                int( column_text )
                return True
            except: 
                return False
        def is_float( column_text ):
            try:
                float( column_text )
                return True
            except: 
                if column_text.strip().lower() == 'na':
                    return True #na is special cased to be a float
                return False
        
        #
        # Get filters.
        # TODOs: 
        # (a) might be useful to move this into each datatype's set_meta method;
        # (b) could look at first N lines to ensure GTF attribute types are consistent.
        #
        filters = []
        # HACK: first 8 fields are for drawing, so start filter column index at 9.
        filter_col = 8
        if isinstance( self.original_dataset.datatype, Gff ):
            # Can filter by score and GTF attributes.
            filters = [ { 'name': 'Score', 
                          'type': 'number', 
                          'index': filter_col, 
                          'tool_id': 'Filter1',
                          'tool_exp_name': 'c6' } ]
            filter_col += 1
            if isinstance( self.original_dataset.datatype, Gtf ):
                # Create filters based on dataset metadata.
                for name, a_type in self.original_dataset.metadata.attribute_types.items():
                    if a_type in [ 'int', 'float' ]:
                        filters.append( 
                            { 'name': name,
                              'type': 'number', 
                              'index': filter_col, 
                              'tool_id': 'gff_filter_by_attribute',
                              'tool_exp_name': name } )
                        filter_col += 1

                '''
                # Old code: use first line in dataset to find attributes.
                for i, line in enumerate( open(self.original_dataset.file_name) ):
                    if not line.startswith('#'):
                        # Look at first line for attributes and types.
                        attributes = parse_gff_attributes( line.split('\t')[8] )
                        for attr, value in attributes.items():
                            # Get attribute type.
                            if is_int( value ):
                                attr_type = 'int'
                            elif is_float( value ):
                                attr_type = 'float'
                            else:
                                attr_type = 'str'
                            # Add to filters.
                            if attr_type is not 'str':
                                filters.append( { 'name': attr, 'type': attr_type, 'index': filter_col } )
                                filter_col += 1
                        break
                '''
        elif isinstance( self.original_dataset.datatype, Bed ):
            # Can filter by score column only.
            filters = [ { 'name': 'Score', 
                          'type': 'number', 
                          'index': filter_col, 
                          'tool_id': 'Filter1',
                          'tool_exp_name': 'c5'
                           } ]

        return filters


class TabixDataProvider( FilterableMixin, TracksDataProvider ):
    """
    Tabix index data provider for the Galaxy track browser.
    """
    
    col_name_data_attr_mapping = { 4 : { 'index': 4 , 'name' : 'Score' } }
        
    def get_iterator( self, chrom, start, end ):
        start, end = int(start), int(end)
        if end >= (2<<29):
            end = (2<<29 - 1) # Tabix-enforced maximum
                    
        bgzip_fname = self.dependencies['bgzip'].file_name
        
        tabix = ctabix.Tabixfile(bgzip_fname, index_filename=self.converted_dataset.file_name)
        
        # If chrom is not found in indexes, try removing the first three 
        # characters (e.g. 'chr') and see if that works. This enables the
        # provider to handle chrome names defined as chrXXX and as XXX.
        chrom = str(chrom)
        if chrom not in tabix.contigs and chrom.startswith("chr") and (chrom[3:] in tabix.contigs):
            chrom = chrom[3:]
        
        return tabix.fetch(reference=chrom, start=start, end=end)
                
    def write_data_to_file( self, chrom, start, end, filename ):
        iterator = self.get_iterator( chrom, start, end )
        out = open( filename, "w" )
        for line in iterator:
            out.write( "%s\n" % line )
        out.close()

#
# -- Interval data providers --
#

class IntervalDataProvider( TracksDataProvider ):
    """
    Processes BED data from native format to payload format.
    
    Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
    """
    
    def get_iterator( self, chrom, start, end ):
        raise Exception( "Unimplemented Function" )
            
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        """
        Provides
        """
        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <strand> ]
        # 
        # First three entries are mandatory, others are optional.
        #
        filter_cols = from_json_string( kwargs.get( "filter_cols", "[]" ) )
        no_detail = ( "no_detail" in kwargs )
        rval = []
        message = None
        # Subtract one b/c columns are 1-based but indices are 0-based.
        col_fn = lambda col: None if col is None else col - 1
        start_col = self.original_dataset.metadata.startCol - 1
        end_col = self.original_dataset.metadata.endCol - 1
        strand_col = col_fn( self.original_dataset.metadata.strandCol )
        name_col = col_fn( self.original_dataset.metadata.nameCol )
        for count, line in enumerate( iterator ):
            if count < start_val:
                continue
            if max_vals and count-start_val >= max_vals:
                message = ERROR_MAX_VALS % ( max_vals, "features" )
                break
            
            feature = line.split()
            length = len(feature)
            # Unique id is just a hash of the line
            payload = [ hash(line), int( feature[start_col] ), int( feature [end_col] ) ]

            if no_detail:
                rval.append( payload )
                continue

            # Name, strand.
            if name_col:
                payload.append( feature[name_col] )
            if strand_col:
                # Put empty name as placeholder.
                if not name_col: payload.append( "" )
                payload.append( feature[strand_col] )

            # Score (filter data)    
            if length >= 5 and filter_cols and filter_cols[0] == "Score":
                try:
                    payload.append( float( feature[4] ) )
                except:
                    payload.append( feature[4] )

            rval.append( payload )

        return { 'data': rval, 'message': message }

    def write_data_to_file( self, chrom, start, end, filename ):
        raise Exception( "Unimplemented Function" )

class IntervalTabixDataProvider( TabixDataProvider, IntervalDataProvider ):
    """
    Provides data from a BED file indexed via tabix.
    """
    pass


#
# -- BED data providers --
#

class BedDataProvider( TracksDataProvider ):
    """
    Processes BED data from native format to payload format.
    
    Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
    """
    
    def get_iterator( self, chrom, start, end ):
        raise Exception( "Unimplemented Method" )
            
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        """
        Provides
        """
        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <strand>, <thick_start>, 
        #   <thick_end>, <blocks> ]
        # 
        # First three entries are mandatory, others are optional.
        #
        filter_cols = from_json_string( kwargs.get( "filter_cols", "[]" ) )
        no_detail = ( "no_detail" in kwargs )
        rval = []
        message = None
        for count, line in enumerate( iterator ):
            if count < start_val:
                continue
            if max_vals and count-start_val >= max_vals:
                message = ERROR_MAX_VALS % ( max_vals, "features" )
                break
            # TODO: can we use column metadata to fill out payload?
            # TODO: use function to set payload data

            feature = line.split()
            length = len(feature)
            # Unique id is just a hash of the line
            payload = [ hash(line), int(feature[1]), int(feature[2]) ]

            if no_detail:
                rval.append( payload )
                continue

            # Simpler way to add stuff, but type casting is not done.
            # Name, score, strand, thick start, thick end.
            #end = min( len( feature ), 8 )
            #payload.extend( feature[ 3:end ] )

            # Name, strand, thick start, thick end.
            if length >= 4:
                payload.append(feature[3])
            if length >= 6:
                payload.append(feature[5])
            if length >= 8:
                payload.append(int(feature[6]))
                payload.append(int(feature[7]))

            # Blocks.
            if length >= 12:
                block_sizes = [ int(n) for n in feature[10].split(',') if n != '']
                block_starts = [ int(n) for n in feature[11].split(',') if n != '' ]
                blocks = zip( block_sizes, block_starts )
                payload.append( [ ( int(feature[1]) + block[1], int(feature[1]) + block[1] + block[0] ) for block in blocks ] )

            # Score (filter data)    
            if length >= 5 and filter_cols and filter_cols[0] == "Score":
                try:
                    payload.append( float( feature[4] ) )
                except:
                    payload.append( feature[4] )

            rval.append( payload )

        return { 'data': rval, 'message': message }

    def write_data_to_file( self, chrom, start, end, filename ):
        iterator = self.get_iterator( chrom, start, end )
        out = open( filename, "w" )
        for line in iterator:
            out.write( "%s\n" % line )
        out.close()
        
class BedTabixDataProvider( TabixDataProvider, BedDataProvider ):
    """
    Provides data from a BED file indexed via tabix.
    """
    pass
    
class RawBedDataProvider( BedDataProvider ):
    """
    Provide data from BED file.

    NOTE: this data provider does not use indices, and hence will be very slow
    for large datasets.
    """

    def get_iterator( self, chrom=None, start=None, end=None ):
        def line_filter_iter():
            for line in open( self.original_dataset.file_name ):
                if line.startswith( "track" ) or line.startswith( "browser" ):
                    continue
                feature = line.split()
                feature_chrom = feature[0]
                feature_start = int( feature[1] )
                feature_end = int( feature[2] )
                if ( chrom is not None and feature_chrom != chrom ) \
                    or ( start is not None and feature_start > int( end ) ) \
                    or ( end is not None and feature_end < int( start ) ):
                    continue
                yield line
        return line_filter_iter()

#
# -- VCF data providers --
#

class VcfDataProvider( TracksDataProvider ):
    """
    Abstract class that processes VCF data from native format to payload format.

    Payload format: TODO
    """
    
    col_name_data_attr_mapping = { 'Qual' : { 'index': 6 , 'name' : 'Qual' } }
    
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        """
        Returns a dict with the following attributes:
            data - a list of variants with the format 
                [<guid>, <start>, <end>, <name>, cigar, seq] 

            message - error/informative message
        """
        rval = []
        message = None

        def get_mapping( ref, alt ):
            """
            Returns ( offset, new_seq, cigar ) tuple that defines mapping of 
            alt to ref. Cigar format is an array of [ op_index, length ] pairs 
            where op_index is the 0-based index into the string "MIDNSHP=X"
            """

            cig_ops = "MIDNSHP=X"

            ref_len = len( ref )
            alt_len = len( alt )

            # Substitutions?
            if ref_len == alt_len:
                return 0, alt, [ [ cig_ops.find( "M" ), ref_len ] ]

            # Deletions?
            alt_in_ref_index = ref.find( alt )
            if alt_in_ref_index != -1:
                return alt_in_ref_index, ref[ alt_in_ref_index + 1: ], [ [ cig_ops.find( "D" ), ref_len - alt_len ] ]

            # Insertions?
            ref_in_alt_index = alt.find( ref )
            if ref_in_alt_index != -1:
                return ref_in_alt_index, alt[ ref_in_alt_index + 1: ], [ [ cig_ops.find( "I" ), alt_len - ref_len ] ]

        # Pack data.
        for count, line in enumerate( iterator ):
            if count < start_val:
                continue
            if max_vals and count-start_val >= max_vals:
                message = ERROR_MAX_VALS % ( max_vals, "features" )
                break

            feature = line.split()
            start = int( feature[1] ) - 1
            ref = feature[3]
            alts = feature[4]

            # HACK? alts == '.' --> monomorphism.
            if alts == '.':
                alts = ref

            # Pack variants.
            for alt in alts.split(","):
                offset, new_seq, cigar = get_mapping( ref, alt )
                start += offset
                end = start + len( new_seq )

                # Pack line.
                payload = [ hash( line ), 
                            start, 
                            end,
                            # ID:
                            feature[2],
                            cigar,
                            # TODO? VCF does not have strand, so default to positive.
                            "+",
                            new_seq,
                            float( feature[5] ) ]
                rval.append(payload)

        return { 'data': rval, 'message': message }

    def write_data_to_file( self, chrom, start, end, filename ):
        iterator = self.get_iterator( chrom, start, end )
        out = open( filename, "w" )
        for line in iterator:
            out.write( "%s\n" % line )
        out.close()

class VcfTabixDataProvider( TabixDataProvider, VcfDataProvider ):
    """
    Provides data from a VCF file indexed via tabix.
    """
    pass

class RawVcfDataProvider( VcfDataProvider ):
    """
    Provide data from VCF file.

    NOTE: this data provider does not use indices, and hence will be very slow
    for large datasets.
    """

    def get_iterator( self, chrom, start, end ):
        def line_filter_iter():
            for line in open( self.original_dataset.file_name ):
                if line.startswith("#"):
                    continue
                variant = line.split()
                variant_chrom, variant_start, id, ref, alts = variant[ 0:5 ]
                variant_start = int( variant_start )
                longest_alt = -1
                for alt in alts:
                    if len( alt ) > longest_alt:
                        longest_alt = len( alt )
                variant_end = variant_start + abs( len( ref ) - longest_alt )
                if variant_chrom != chrom or variant_start > int( end ) or variant_end < int( start ):
                    continue
                yield line
        return line_filter_iter()

class SummaryTreeDataProvider( TracksDataProvider ):
    """
    Summary tree data provider for the Galaxy track browser. 
    """
    
    CACHE = LRUCache(20) # Store 20 recently accessed indices for performance
    
    def valid_chroms( self ):
        st = summary_tree_from_file( self.converted_dataset.file_name )
        return st.chrom_blocks.keys()
        
    
    def get_summary( self, chrom, start, end, **kwargs ):
        filename = self.converted_dataset.file_name
        st = self.CACHE[filename]
        if st is None:
            st = summary_tree_from_file( self.converted_dataset.file_name )
            self.CACHE[filename] = st

        # If chrom is not found in blocks, try removing the first three 
        # characters (e.g. 'chr') and see if that works. This enables the
        # provider to handle chrome names defined as chrXXX and as XXX.
        if chrom in st.chrom_blocks:
            pass
        elif chrom[3:] in st.chrom_blocks:
            chrom = chrom[3:]
        else:
            return None

        resolution = max(1, ceil(float(kwargs['resolution'])))

        level = ceil( log( resolution, st.block_size ) ) - 1
        level = int(max( level, 0 ))
        if level <= 1:
            return "detail"

        stats = st.chrom_stats[chrom]
        results = st.query(chrom, int(start), int(end), level)
        if results == "detail" or results == "draw":
            return results
        else:
            return results, stats[level]["max"], stats[level]["avg"], stats[level]["delta"]
            
    def has_data( self, chrom ):
        """
        Returns true if dataset has data for this chrom
        """
        
        # Get summary tree.
        filename = self.converted_dataset.file_name
        st = self.CACHE[filename]
        if st is None:
            st = summary_tree_from_file( self.converted_dataset.file_name )
            self.CACHE[filename] = st
            
        # Check for data.
        return st.chrom_blocks.get(chrom, None) is not None or (chrom and st.chrom_blocks.get(chrom[3:], None) is not None)

class BamDataProvider( TracksDataProvider, FilterableMixin ):
    """
    Provides access to intervals from a sorted indexed BAM file.
    """
    
    def get_filters( self ):
        """
        Returns filters for dataset.
        """
        # HACK: first 7 fields are for drawing, so start filter column index at 7.
        filter_col = 7
        filters = []
        filters.append( { 'name': 'Mapping Quality', 
                        'type': 'number', 
                        'index': filter_col
                         } )
        return filters
    
    
    def write_data_to_file( self, chrom, start, end, filename ):
        """
        Write reads in [chrom:start-end] to file.
        """
        
        # Open current BAM file using index.
        start, end = int(start), int(end)
        bamfile = csamtools.Samfile( filename=self.original_dataset.file_name, mode='rb', \
                                     index_filename=self.converted_dataset.file_name )
        try:
            data = bamfile.fetch(start=start, end=end, reference=chrom)
        except ValueError, e:
            # Some BAM files do not prefix chromosome names with chr, try without
            if chrom.startswith( 'chr' ):
                try:
                    data = bamfile.fetch( start=start, end=end, reference=chrom[3:] )
                except ValueError:
                    return None
            else:
                return None
        
        # Write new BAM file.
        # TODO: write headers as well?
        new_bamfile = csamtools.Samfile( template=bamfile, filename=filename, mode='wb' )
        for i, read in enumerate( data ):
            new_bamfile.write( read )
        new_bamfile.close()
        
        # Cleanup.
        bamfile.close()
        
    def get_iterator( self, chrom, start, end ):
        """
        Returns an iterator that provides data in the region chrom:start-end
        """
        start, end = int(start), int(end)
        orig_data_filename = self.original_dataset.file_name
        index_filename = self.converted_dataset.file_name
        
        # Attempt to open the BAM file with index
        bamfile = csamtools.Samfile( filename=orig_data_filename, mode='rb', index_filename=index_filename )
        try:
            data = bamfile.fetch(start=start, end=end, reference=chrom)
        except ValueError, e:
            # Some BAM files do not prefix chromosome names with chr, try without
            if chrom.startswith( 'chr' ):
                try:
                    data = bamfile.fetch( start=start, end=end, reference=chrom[3:] )
                except ValueError:
                    return None
            else:
                return None
        return data
                
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        """
        Returns a dict with the following attributes:
            data - a list of reads with the format 
                    [<guid>, <start>, <end>, <name>, <read_1>, <read_2>, [empty], <mapq_scores>]
                where <read_1> has the format
                    [<start>, <end>, <cigar>, <strand>, <read_seq>]
                and <read_2> has the format
                    [<start>, <end>, <cigar>, <strand>, <read_seq>]
                Field 7 is empty so that mapq scores' location matches that in single-end reads.
                For single-end reads, read has format:
                    [<guid>, <start>, <end>, <name>, <cigar>, <strand>, <seq>, <mapq_score>]
                
                NOTE: read end and sequence data are not valid for reads outside of
                requested region and should not be used.
            
            max_low - lowest coordinate for the returned reads
            max_high - highest coordinate for the returned reads
            message - error/informative message
        """
        # No iterator indicates no reads.
        if iterator is None:
            return { 'data': [], 'message': None }
        
        # Decode strand from read flag.
        def decode_strand( read_flag, mask ):
            strand_flag = ( read_flag & mask == 0 )
            if strand_flag:
                return "+"
            else:
                return "-"
                
        # Encode reads as list of lists.
        results = []
        paired_pending = {}
        unmapped = 0
        message = None
        for count, read in enumerate( iterator ):
            if count < start_val:
                continue
            if ( count - start_val - unmapped ) >= max_vals:
                message = ERROR_MAX_VALS % ( max_vals, "reads" )
                break
                
            # If not mapped, skip read.
            is_mapped = ( read.flag & 0x0004 == 0 )
            if not is_mapped:
                unmapped += 1
                continue
                            
            qname = read.qname
            seq = read.seq
            strand = decode_strand( read.flag, 0x0010 )
            if read.cigar is not None:
                read_len = sum( [cig[1] for cig in read.cigar] ) # Use cigar to determine length
            else:
                read_len = len(seq) # If no cigar, just use sequence length

            if read.is_proper_pair:
                if qname in paired_pending: # one in dict is always first
                    pair = paired_pending[qname]
                    results.append( [ "%i_%s" % ( pair['start'], qname ), 
                                      pair['start'], 
                                      read.pos + read_len, 
                                      qname, 
                                      [ pair['start'], pair['end'], pair['cigar'], pair['strand'], pair['seq'] ], 
                                      [ read.pos, read.pos + read_len, read.cigar, strand, seq ],
                                      None, [ pair['mapq'], read.mapq ]
                                     ] )
                    del paired_pending[qname]
                else:
                    paired_pending[qname] = { 'start': read.pos, 'end': read.pos + read_len, 'seq': seq, 'mate_start': read.mpos,
                                              'rlen': read_len, 'strand': strand, 'cigar': read.cigar, 'mapq': read.mapq }
            else:
                results.append( [ "%i_%s" % ( read.pos, qname ), 
                                read.pos, read.pos + read_len, qname, 
                                read.cigar, strand, read.seq, read.mapq ] )
                
        # Take care of reads whose mates are out of range.
        # TODO: count paired reads when adhering to max_vals?
        for qname, read in paired_pending.iteritems():
            if read['mate_start'] < read['start']:
                # Mate is before read.
                read_start = read['mate_start']
                read_end = read['end']
                # Make read_1 start=end so that length is 0 b/c we don't know
                # read length.
                r1 = [ read['mate_start'], read['mate_start'] ]
                r2 = [ read['start'], read['end'], read['cigar'], read['strand'], read['seq'] ]
            else:
                # Mate is after read.
                read_start = read['start']
                # Make read_2 start=end so that length is 0 b/c we don't know
                # read length. Hence, end of read is start of read_2.
                read_end = read['mate_start']
                r1 = [ read['start'], read['end'], read['cigar'], read['strand'], read['seq'] ]
                r2 = [ read['mate_start'], read['mate_start'] ]

            results.append( [ "%i_%s" % ( read_start, qname ), read_start, read_end, qname, r1, r2, [read[ 'mapq' ], 125] ] )
            
        # Clean up. TODO: is this needed? If so, we'll need a cleanup function after processing the data.
        # bamfile.close()
        
        max_low, max_high = get_bounds( results, 1, 2 )
                
        return { 'data': results, 'message': message, 'max_low': max_low, 'max_high': max_high }
        
class SamDataProvider( BamDataProvider ):
    
    def __init__( self, converted_dataset=None, original_dataset=None, dependencies=None ):
        """ Create SamDataProvider. """
        
        # HACK: to use BamDataProvider, original dataset must be BAM and 
        # converted dataset must be BAI. Use BAI from BAM metadata.
        if converted_dataset:
            self.converted_dataset = converted_dataset.metadata.bam_index
            self.original_dataset = converted_dataset
        self.dependencies = dependencies

class BBIDataProvider( TracksDataProvider ):
    """
    BBI data provider for the Galaxy track browser. 
    """
    def valid_chroms( self ):
        # No way to return this info as of now
        return None
        
    def has_data( self, chrom ):
        f, bbi = self._get_dataset()
        all_dat = bbi.query(chrom, 0, 2147483647, 1)
        f.close()
        return all_dat is not None
        
    def get_data( self, chrom, start, end, start_val=0, max_vals=None, **kwargs ):
        # Bigwig has the possibility of it being a standalone bigwig file, in which case we use
        # original_dataset, or coming from wig->bigwig conversion in which we use converted_dataset
        f, bbi = self._get_dataset()
       
        # If the stats kwarg was provide, we compute overall summary data for
        # the entire chromosome, but no reduced data -- currently only
        # providing values used by trackster to determine the default range
        if 'stats' in kwargs:
            # FIXME: use actual chromosome size
            summary = bbi.summarize( chrom, 0, 214783647, 1 )
            f.close()
            if summary is None:
                return None
            else:
                # Does the summary contain any defined values?
                valid_count = summary.valid_count[0]
                if summary.valid_count < 1:
                    return None

                # Compute $\mu \pm 2\sigma$ to provide an estimate for upper and lower
                # bounds that contain ~95% of the data.
                mean = summary.sum_data[0] / valid_count
                var = summary.sum_squares[0] - mean
                if valid_count > 1:
                    var /= valid_count - 1
                sd = numpy.sqrt( var )

                return dict( data=dict( min=summary.min_val[0], max=summary.max_val[0], mean=mean, sd=sd ) )

        start = int(start)
        end = int(end)

        # The following seems not to work very well, for example it will only return one
        # data point if the tile is 1280px wide. Not sure what the intent is.

        # The first zoom level for BBI files is 640. If too much is requested, it will look at each block instead
        # of summaries. The calculation done is: zoom <> (end-start)/num_points/2.
        # Thus, the optimal number of points is (end-start)/num_points/2 = 640
        # num_points = (end-start) / 1280
        #num_points = (end-start) / 1280
        #if num_points < 1:
        #    num_points = end - start
        #else:
        #    num_points = min(num_points, 500)

        # For now, we'll do 1000 data points by default However, the summaries
        # don't seem to work when a summary pixel corresponds to less than one
        # datapoint, so we prevent that. 
        # FIXME: need to switch over to using the full data at high levels of
        # detail.
        num_points = min( 1000, end - start )

        summary = bbi.summarize( chrom, start, end, num_points )
        f.close()

        result = []

        if summary:
            #mean = summary.sum_data / summary.valid_count
            

            ## Standard deviation by bin, not yet used
            ## var = summary.sum_squares - mean
            ## var /= minimum( valid_count - 1, 1 )
            ## sd = sqrt( var )
        
            pos = start
            step_size = (end - start) / num_points

            for i in range( num_points ):
                result.append( (pos, float_nan( summary.sum_data[i] ) ) )
                pos += step_size
        
        return { 'data': result }

class BigBedDataProvider( BBIDataProvider ):
    def _get_dataset( self ):
        # Nothing converts to bigBed so we don't consider converted dataset
        f = open( self.original_dataset.file_name )
        return f, BigBedFile(file=f)

class BigWigDataProvider (BBIDataProvider ):
    def _get_dataset( self ):
        if self.converted_dataset is not None:
            f = open( self.converted_dataset.file_name )
        else:
            f = open( self.original_dataset.file_name )
        return f, BigWigFile(file=f)
            
class IntervalIndexDataProvider( FilterableMixin, TracksDataProvider ):
    """
    Interval index files used only for GFF files.
    """
    col_name_data_attr_mapping = { 4 : { 'index': 4 , 'name' : 'Score' } }
    
    def write_data_to_file( self, chrom, start, end, filename ):
        source = open( self.original_dataset.file_name )
        index = Indexes( self.converted_dataset.file_name )
        out = open( filename, 'w' )
        for start, end, offset in index.find(chrom, start, end):
            source.seek( offset )
            
            reader = GFFReaderWrapper( source, fix_strand=True )
            feature = reader.next()
            for interval in feature.intervals:
                out.write( '\t'.join( interval.fields ) + '\n' )
        out.close()
        
    def get_iterator( self, chrom, start, end ):
        """
        Returns an array with values: (a) source file and (b) an iterator that
        provides data in the region chrom:start-end
        """
        start, end = int(start), int(end)
        source = open( self.original_dataset.file_name )
        index = Indexes( self.converted_dataset.file_name )

        # If chrom is not found in indexes, try removing the first three 
        # characters (e.g. 'chr') and see if that works. This enables the
        # provider to handle chrome names defined as chrXXX and as XXX.
        chrom = str(chrom)
        if chrom not in index.indexes and chrom[3:] in index.indexes:
            chrom = chrom[3:]
            
        return index.find(chrom, start, end)

    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        results = []
        message = None
        source = open( self.original_dataset.file_name )

        #
        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <score>, <strand>, <thick_start>,
        #   <thick_end>, <blocks> ]
        # 
        # First three entries are mandatory, others are optional.
        #
        filter_cols = from_json_string( kwargs.get( "filter_cols", "[]" ) )
        no_detail = ( "no_detail" in kwargs )
        for count, val in enumerate( iterator ):
            start, end, offset = val[0], val[1], val[2]
            if count < start_val:
                continue
            if count-start_val >= max_vals:
                message = ERROR_MAX_VALS % ( max_vals, "features" )
                break
            source.seek( offset )
            # TODO: can we use column metadata to fill out payload?
            
            # GFF dataset.
            reader = GFFReaderWrapper( source, fix_strand=True )
            feature = reader.next()
            payload = package_gff_feature( feature, no_detail, filter_cols )
            payload.insert( 0, offset )

            results.append( payload )

        return { 'data': results, 'message': message }

class RawGFFDataProvider( TracksDataProvider ):
    """
    Provide data from GFF file that has not been indexed.
    
    NOTE: this data provider does not use indices, and hence will be very slow
    for large datasets.
    """
    
    def get_iterator( self, chrom, start, end ):
        """
        Returns an iterator that provides data in the region chrom:start-end as well as
        a file offset.
        """
        start, end = int( start ), int( end )
        source = open( self.original_dataset.file_name )
    
        def features_in_region_iter():
            offset = 0
            for feature in GFFReaderWrapper( source, fix_strand=True ):
                # Only provide features that are in region.
                feature_start, feature_end = convert_gff_coords_to_bed( [ feature.start, feature.end ] )
                if feature.chrom == chrom and feature_end > start and feature_start < end:
                    yield feature, offset
                offset += feature.raw_size
        return features_in_region_iter()
            
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        """
        Process data from an iterator to a format that can be provided to client.
        """
        filter_cols = from_json_string( kwargs.get( "filter_cols", "[]" ) )
        no_detail = ( "no_detail" in kwargs )
        results = []
        message = None

        for count, ( feature, offset ) in enumerate( iterator ):
            if count < start_val:
                continue
            if count-start_val >= max_vals:
                message = ERROR_MAX_VALS % ( max_vals, "reads" )
                break
                
            payload = package_gff_feature( feature, no_detail=no_detail, filter_cols=filter_cols )
            payload.insert( 0, offset )
            results.append( payload )

            
        return { 'data': results, 'message': message }
        
class GtfTabixDataProvider( TabixDataProvider ):
    """
    Returns data from GTF datasets that are indexed via tabix.
    """
    
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        # Loop through lines and group by transcript_id; each group is a feature.
        
        # TODO: extend this code or use code in gff_util to process GFF/3 as well
        # and then create a generic GFFDataProvider that can be used with both
        # raw and tabix datasets.
        features = {}
        for count, line in enumerate( iterator ):
            line_attrs = parse_gff_attributes( line.split('\t')[8] )
            transcript_id = line_attrs[ 'transcript_id' ]
            if transcript_id in features:
                feature = features[ transcript_id ]
            else:
                feature = []
                features[ transcript_id ] = feature
            feature.append( GFFInterval( None, line.split( '\t') ) )
                                
        # Process data.
        filter_cols = from_json_string( kwargs.get( "filter_cols", "[]" ) )
        no_detail = ( "no_detail" in kwargs )
        results = []
        message = None

        for count, intervals in enumerate( features.values() ):
            if count < start_val:
                continue
            if count-start_val >= max_vals:
                message = ERROR_MAX_VALS % ( max_vals, "reads" )
                break
            
            feature = GFFFeature( None, intervals=intervals )    
            payload = package_gff_feature( feature, no_detail=no_detail, filter_cols=filter_cols )
            payload.insert( 0, feature.intervals[ 0 ].attributes[ 'transcript_id' ] )
            results.append( payload )
                        
        return { 'data': results, 'message': message }

#
# -- ENCODE Peak data providers.
#

class ENCODEPeakDataProvider( TracksDataProvider ):
    """
    Abstract class that processes ENCODEPeak data from native format to payload format.
    
    Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
    """
    
    def get_iterator( self, chrom, start, end ):
        raise "Unimplemented Method"
            
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        """
        Provides
        """
        
        ## FIXMEs:
        # (1) should be able to unify some of this code with BedDataProvider.process_data
        # (2) are optional number of parameters supported?
        
        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <strand>, <thick_start>,
        #   <thick_end>, <blocks> ]
        # 
        # First three entries are mandatory, others are optional.
        #
        no_detail = ( "no_detail" in kwargs )
        rval = []
        message = None
        for count, line in enumerate( iterator ):
            if count < start_val:
                continue
            if max_vals and count-start_val >= max_vals:
                message = ERROR_MAX_VALS % ( max_vals, "features" )
                break

            feature = line.split()
            length = len( feature )
            
            # Feature initialization.
            payload = [
                # GUID is just a hash of the line
                hash( line ),
                # Add start, end.
                int( feature[1] ), 
                int( feature[2] )
                        ]
            
            if no_detail:
                rval.append( payload )
                continue

            # Extend with additional data.
            payload.extend( [
                # Add name, strand.
                feature[3], 
                feature[5],
                # Thick start, end are feature start, end for now.
                int( feature[1] ),
                int( feature[2] ),
                # No blocks.
                None,
                # Filtering data: Score, signalValue, pValue, qValue.
                float( feature[4] ),
                float( feature[6] ),
                float( feature[7] ),
                float( feature[8] )
                ] )

            rval.append( payload )

        return { 'data': rval, 'message': message }

    def write_data_to_file( self, chrom, start, end, filename ):
        iterator = self.get_iterator( chrom, start, end )
        out = open( filename, "w" )
        for line in iterator:
            out.write( "%s\n" % line )
        out.close()
        
class ENCODEPeakTabixDataProvider( TabixDataProvider, ENCODEPeakDataProvider ):
    """
    Provides data from an ENCODEPeak dataset indexed via tabix.
    """
    
    def get_filters( self ):
        """
        Returns filters for dataset.
        """
        # HACK: first 8 fields are for drawing, so start filter column index at 9.
        filter_col = 8
        filters = []
        filters.append( { 'name': 'Score', 
                          'type': 'number', 
                          'index': filter_col,
                          'tool_id': 'Filter1',
                          'tool_exp_name': 'c6' } )
        filter_col += 1
        filters.append( { 'name': 'Signal Value', 
                          'type': 'number', 
                          'index': filter_col,
                          'tool_id': 'Filter1',
                          'tool_exp_name': 'c7' } )
        filter_col += 1
        filters.append( { 'name': 'pValue', 
                        'type': 'number', 
                        'index': filter_col,
                        'tool_id': 'Filter1',
                        'tool_exp_name': 'c8' } )
        filter_col += 1
        filters.append( { 'name': 'qValue', 
                        'type': 'number', 
                        'index': filter_col,
                        'tool_id': 'Filter1',
                        'tool_exp_name': 'c9' } )
        return filters
               
#        
# -- Helper methods. --
#

# Mapping from dataset type name to a class that can fetch data from a file of that
# type. First key is converted dataset type; if result is another dict, second key
# is original dataset type. TODO: This needs to be more flexible.
dataset_type_name_to_data_provider = {
    "tabix": { 
        Vcf: VcfTabixDataProvider,
        Bed: BedTabixDataProvider,
        Gtf: GtfTabixDataProvider,
        ENCODEPeak: ENCODEPeakTabixDataProvider,
        Interval: IntervalTabixDataProvider,
        "default" : TabixDataProvider },
    "interval_index": IntervalIndexDataProvider,
    "bai": BamDataProvider,
    "bam": SamDataProvider,
    "summary_tree": SummaryTreeDataProvider,
    "bigwig": BigWigDataProvider,
    "bigbed": BigBedDataProvider
}

def get_data_provider( name=None, original_dataset=None ):
    """
    Returns data provider class by name and/or original dataset.
    """
    data_provider = None
    if name:
        value = dataset_type_name_to_data_provider[ name ]
        if isinstance( value, dict ):
            # Get converter by dataset extension; if there is no data provider,
            # get the default.
            data_provider = value.get( original_dataset.datatype.__class__, value.get( "default" ) )
        else:
            data_provider = value
    elif original_dataset:
        # Look up data provider from datatype's informaton.
        try:
            # Get data provider mapping and data provider for 'data'. If 
            # provider available, use it; otherwise use generic provider.
            _ , data_provider_mapping = original_dataset.datatype.get_track_type()
            if 'data_standalone' in data_provider_mapping:
                data_provider_name = data_provider_mapping[ 'data_standalone' ]
            else:
                data_provider_name = data_provider_mapping[ 'data' ]
            if data_provider_name:
                data_provider = get_data_provider( name=data_provider_name, original_dataset=original_dataset )
            else: 
                data_provider = TracksDataProvider
        except:
            pass
    return data_provider

def package_gff_feature( feature, no_detail=False, filter_cols=[] ):
    """ Package a GFF feature in an array for data providers. """
    feature = convert_gff_coords_to_bed( feature )
    
    # No detail means only start, end.
    if no_detail:
        return [ feature.start, feature.end ]
    
    # Return full feature.
    payload = [ feature.start, 
                feature.end, 
                feature.name(),
                feature.strand,
                # No notion of thick start, end in GFF, so make everything
                # thick.
                feature.start,
                feature.end
                ]
    
    # HACK: ignore interval with name 'transcript' from feature. 
    # Cufflinks puts this interval in each of its transcripts, 
    # and they mess up trackster by covering the feature's blocks.
    # This interval will always be a feature's first interval,
    # and the GFF's third column is its feature name.
    feature_intervals = feature.intervals
    if feature.intervals[0].fields[2] == 'transcript':
        feature_intervals = feature.intervals[1:]
    # Add blocks.
    block_sizes = [ (interval.end - interval.start ) for interval in feature_intervals ]
    block_starts = [ ( interval.start - feature.start ) for interval in feature_intervals ]
    blocks = zip( block_sizes, block_starts )
    payload.append( [ ( feature.start + block[1], feature.start + block[1] + block[0] ) for block in blocks ] )
    
    # Add filter data to payload.
    for col in filter_cols:
        if col == "Score":
            if feature.score == 'nan':
                payload.append( feature.score )
            else:
                try:
                    f = float( feature.score )
                    payload.append( f )
                except:
                    payload.append( feature.score )
        elif col in feature.attributes:
            if feature.attributes[col] == 'nan':
                payload.append( feature.attributes[col] )
            else:
                try:
                    f = float( feature.attributes[col] )
                    payload.append( f )
                except:
                    payload.append( feature.attributes[col] )
        else:
            # Dummy value.
            payload.append( 0 )
    return payload
