"""
Data providers for tracks visualizations.
"""

import sys
from math import floor, ceil, log, pow
import pkg_resources
pkg_resources.require( "bx-python" )
if sys.version_info[:2] == (2, 4):
    pkg_resources.require( "ctypes" )
pkg_resources.require( "pysam" )
pkg_resources.require( "numpy" )
from galaxy.datatypes.util.gff_util import *
from galaxy.util.json import from_json_string
from bx.interval_index_file import Indexes
from bx.arrays.array_tree import FileArrayTreeDict
from bx.bbi.bigwig_file import BigWigFile
from galaxy.util.lrucache import LRUCache
from galaxy.visualization.tracks.summary import *
import galaxy_utils.sequence.vcf
from galaxy.datatypes.tabular import Vcf
from galaxy.datatypes.interval import Bed, Gff, Gtf
from galaxy.datatypes.util.gff_util import parse_gff_attributes

from pysam import csamtools, ctabix

MAX_VALS = 5000 # only display first MAX_VALS features
ERROR_MAX_VALS = "Only the first " + str(MAX_VALS) + " %s in the region denoted by the red line are displayed."

# Return None instead of NaN to pass jQuery 1.4's strict JSON
def float_nan(n):
    if n != n: # NaN != NaN
        return None
    else:
        return float(n)

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
        # Override.
        pass
        
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
        # Override.
        pass
        
    def get_data( self, chrom, start, end, **kwargs ):
        """ Returns data in region defined by chrom, start, and end. """
        # Override.
        pass
        
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

class BamDataProvider( TracksDataProvider ):
    """
    Provides access to intervals from a sorted indexed BAM file.
    """
    
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
    
    def get_data( self, chrom, start, end, **kwargs ):
        """
        Fetch intervals in the region 
        """
        start, end = int(start), int(end)
        orig_data_filename = self.original_dataset.file_name
        index_filename = self.converted_dataset.file_name
        no_detail = "no_detail" in kwargs
        # Attempt to open the BAM file with index
        bamfile = csamtools.Samfile( filename=orig_data_filename, mode='rb', index_filename=index_filename )
        message = None
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
        # Encode reads as list of lists; each read is a list with the format 
        #   [<guid>, <start>, <end>, <name>, <read_1>, <read_2>] 
        # where <read_1> has the format
        #   [<start>, <end>, <cigar>, ?<read_seq>?]
        # and <read_2> has the format
        #   [<start>, <end>, <cigar>, ?<read_seq>?]
        # For single-end reads, read has format:
        #   [<guid>, <start>, <end>, <name>, cigar, seq] 
        # NOTE: read end and sequence data are not valid for reads outside of
        # requested region and should not be used.
        results = []
        paired_pending = {}
        for read in data:
            if len(results) > MAX_VALS:
                message = ERROR_MAX_VALS % "reads"
                break
            qname = read.qname
            seq = read.seq
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
                                      [ pair['start'], pair['end'], pair['cigar'], pair['seq'] ], 
                                      [ read.pos, read.pos + read_len, read.cigar, seq ] 
                                     ] )
                    del paired_pending[qname]
                else:
                    paired_pending[qname] = { 'start': read.pos, 'end': read.pos + read_len, 'seq': seq, 'mate_start': read.mpos, 'rlen': read_len, 'cigar': read.cigar }
            else:
                results.append( [ "%i_%s" % ( read.pos, qname ), read.pos, read.pos + read_len, qname, read.cigar, read.seq] )
        # Take care of reads whose mates are out of range.
        for qname, read in paired_pending.iteritems():
            if read['mate_start'] < read['start']:
                # Mate is before read.
                read_start = read['mate_start']
                read_end = read['end']
                # Make read_1 start=end so that length is 0 b/c we don't know
                # read length.
                r1 = [ read['mate_start'], read['mate_start'] ]
                r2 = [ read['start'], read['end'], read['cigar'], read['seq'] ]
            else:
                # Mate is after read.
                read_start = read['start']
                # Make read_2 start=end so that length is 0 b/c we don't know
                # read length. Hence, end of read is start of read_2.
                read_end = read['mate_start']
                r1 = [ read['start'], read['end'], read['cigar'], read['seq'] ]
                r2 = [ read['mate_start'], read['mate_start'] ]

            results.append( [ "%i_%s" % ( read_start, qname ), read_start, read_end, qname, r1, r2 ] )

        bamfile.close()
        return { 'data': results, 'message': message }

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
        
    def get_data( self, chrom, start, end, **kwargs ):
        # Bigwig has the possibility of it being a standalone bigwig file, in which case we use
        # original_dataset, or coming from wig->bigwig conversion in which we use converted_dataset
        f, bbi = self._get_dataset()
        
        if 'stats' in kwargs:
            all_dat = bbi.query(chrom, 0, 2147483647, 1)
            f.close()
            if all_dat is None:
                return None
            
            all_dat = all_dat[0] # only 1 summary
            return { 'max': float( all_dat['max'] ), \
                     'min': float( all_dat['min'] ), \
                     'total_frequency': float( all_dat['coverage'] ) }
                     
        start = int(start)
        end = int(end)
        # The first zoom level for BBI files is 640. If too much is requested, it will look at each block instead
        # of summaries. The calculation done is: zoom <> (end-start)/num_points/2.
        # Thus, the optimal number of points is (end-start)/num_points/2 = 640
        # num_points = (end-start) / 1280
        num_points = (end-start) / 1280
        if num_points < 1:
            num_points = end - start
        num_points = max(num_points, 10)

        data = bbi.query(chrom, start, end, num_points)
        f.close()
        
        pos = start
        step_size = (end - start) / num_points
        result = []
        if data:
            for dat_dict in data:
                result.append( (pos, float_nan(dat_dict['mean']) ) )
                pos += step_size
            
        return result

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
                          'type': 'int', 
                          'index': filter_col, 
                          'tool_id': 'Filter1',
                          'tool_exp_name': 'c5' } ]
            filter_col += 1
            if isinstance( self.original_dataset.datatype, Gtf ):
                # Create filters based on dataset metadata.
                for name, a_type in self.original_dataset.metadata.attribute_types.items():
                    if a_type in [ 'int', 'float' ]:
                        filters.append( 
                            { 'name': name,
                              'type': a_type, 
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
                          'type': 'int', 
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
        
        # if os.path.getsize(self.converted_dataset.file_name) == 0:
            # return { 'kind': messages.ERROR, 'message': "Tabix converted size was 0, meaning the input file had invalid values." }
        tabix = ctabix.Tabixfile(bgzip_fname, index_filename=self.converted_dataset.file_name)
        
        # If chrom is not found in indexes, try removing the first three 
        # characters (e.g. 'chr') and see if that works. This enables the
        # provider to handle chrome names defined as chrXXX and as XXX.
        chrom = str(chrom)
        if chrom not in tabix.contigs and chrom.startswith("chr") and (chrom[3:] in tabix.contigs):
            chrom = chrom[3:]
        
        return tabix.fetch(reference=chrom, start=start, end=end)
        
    def get_data( self, chrom, start, end, **kwargs ):
        iterator = self.get_iterator( chrom, start, end )
        return self.process_data(iterator, **kwargs)
     
class IntervalIndexDataProvider( FilterableMixin, TracksDataProvider ):
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
                out.write(interval.raw_line + '\n')
        out.close()
    
    def get_data( self, chrom, start, end, **kwargs ):
        start, end = int(start), int(end)
        source = open( self.original_dataset.file_name )
        index = Indexes( self.converted_dataset.file_name )
        results = []
        count = 0
        message = None

        # If chrom is not found in indexes, try removing the first three 
        # characters (e.g. 'chr') and see if that works. This enables the
        # provider to handle chrome names defined as chrXXX and as XXX.
        chrom = str(chrom)
        if chrom not in index.indexes and chrom[3:] in index.indexes:
            chrom = chrom[3:]

        #
        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <score>, <strand>, <thick_start>,
        #   <thick_end>, <blocks> ]
        # 
        # First three entries are mandatory, others are optional.
        #
        filter_cols = from_json_string( kwargs.get( "filter_cols", "[]" ) )
        no_detail = ( "no_detail" in kwargs )
        for start, end, offset in index.find(chrom, start, end):
            if count >= MAX_VALS:
                message = ERROR_MAX_VALS % "features"
                break
            count += 1
            source.seek( offset )
            # TODO: can we use column metadata to fill out payload?
            # TODO: use function to set payload data
            
            # GFF dataset.
            reader = GFFReaderWrapper( source, fix_strand=True )
            feature = reader.next()
            payload = package_gff_feature( feature, no_detail, filter_cols )
            payload.insert( 0, offset )

            results.append( payload )

        return { 'data': results, 'message': message }
        
class BedDataProvider( TabixDataProvider ):
    """
    Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
    """
        
    def process_data( self, iterator, **kwargs ):
        #
        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <score>, <strand>, <thick_start>,
        #   <thick_end>, <blocks> ]
        # 
        # First three entries are mandatory, others are optional.
        #
        filter_cols = from_json_string( kwargs.get( "filter_cols", "[]" ) )
        no_detail = ( "no_detail" in kwargs )
        count = 0
        rval = []
        message = None
        for line in iterator:
            if count >= MAX_VALS:
                message = ERROR_MAX_VALS % "features"
                break
            count += 1
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
                payload.append( float(feature[4]) )
                
            rval.append( payload )
            
        return { 'data': rval, 'message': message }
        
    def write_data_to_file( self, chrom, start, end, filename ):
        iterator = self.get_iterator( chrom, start, end )
        out = open( filename, "w" )
        for line in iterator:
            out.write( line )
        out.close()
        
class VcfDataProvider( TracksDataProvider ):
    """
    VCF data provider for the Galaxy track browser.

    Payload format: 
    [ uid (offset), start, end, ID, reference base(s), alternate base(s), quality score]
    """

    col_name_data_attr_mapping = { 'Qual' : { 'index': 6 , 'name' : 'Qual' } }

    def process_data( self, iterator, **kwargs ):
        rval = []
        count = 0
        message = None
        
        reader = galaxy_utils.sequence.vcf.Reader( iterator )
        for line in reader:
            if count >= MAX_VALS:
                message = ERROR_MAX_VALS % "features"
                break
            count += 1
            
            feature = line.split()
            payload = [ hash(line), vcf_line.pos-1, vcf_line.pos, \
                        # ID: 
                        feature[2], \
                        # reference base(s):
                        feature[3], \
                        # alternative base(s)
                        feature[4], \
                        # phred quality score
                        int( feature[5] )]
            rval.append(payload)

        return { 'data_type' : 'vcf', 'data': rval, 'message': message }

class GFFDataProvider( TracksDataProvider ):
    """
    Provide data from GFF file.
    
    NOTE: this data provider does not use indices, and hence will be very slow
    for large datasets. 
    """
    def get_data( self, chrom, start, end, **kwargs ):
        start, end = int( start ), int( end )
        source = open( self.original_dataset.file_name )
        results = []
        count = 0
        message = None
        offset = 0
        
        for feature in GFFReaderWrapper( source, fix_strand=True ):
            feature_start, feature_end = convert_gff_coords_to_bed( [ feature.start, feature.end ] )
            if feature.chrom != chrom or feature_start < start or feature_end > end:
                continue
            if count >= MAX_VALS:
                message = ERROR_MAX_VALS % "features"
                break
            count += 1
            payload = package_gff_feature( feature )
            payload.insert( 0, offset )
            results.append( payload )
            offset += feature.raw_size
            
        return { 'data': results, 'message': message }
       
#        
# Helper methods.
#

# Mapping from dataset type name to a class that can fetch data from a file of that
# type. First key is converted dataset type; if result is another dict, second key
# is original dataset type. TODO: This needs to be more flexible.
dataset_type_name_to_data_provider = {
    "tabix": { Vcf: VcfDataProvider, Bed: BedDataProvider, "default" : TabixDataProvider },
    "interval_index": IntervalIndexDataProvider,
    "bai": BamDataProvider,
    "summary_tree": SummaryTreeDataProvider,
    "bigwig": BigWigDataProvider,
    "bigbed": BigBedDataProvider
}

def get_data_provider( name=None, original_dataset=None ):
    """
    Returns data provider class by name and/or original dataset.
    """
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
    
    # HACK: remove interval with name 'transcript' from feature. 
    # Cufflinks puts this interval in each of its transcripts, 
    # and they mess up trackster by covering the feature's blocks.
    # This interval will always be a feature's first interval,
    # and the GFF's third column is its feature name. 
    if feature.intervals[0].fields[2] == 'transcript':
        feature.intervals = feature.intervals[1:]
    # Add blocks.
    block_sizes = [ (interval.end - interval.start ) for interval in feature.intervals ]
    block_starts = [ ( interval.start - feature.start ) for interval in feature.intervals ]
    blocks = zip( block_sizes, block_starts )
    payload.append( [ ( feature.start + block[1], feature.start + block[1] + block[0] ) for block in blocks ] )
    
    # Add filter data to payload.
    for col in filter_cols:
        if col == "Score":
            payload.append( feature.score )
        elif col in feature.attributes:
            payload.append( feature.attributes[col] )
        else:
            # Dummy value.
            payload.append( "na" )
    return payload
