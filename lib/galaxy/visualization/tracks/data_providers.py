"""
Data providers for tracks visualizations.
"""

from math import floor, ceil, log, pow
import pkg_resources
pkg_resources.require( "bx-python" ); pkg_resources.require( "pysam" ); pkg_resources.require( "numpy" )
from bx.interval_index_file import Indexes
from bx.arrays.array_tree import FileArrayTreeDict
from galaxy.util.lrucache import LRUCache
from galaxy.visualization.tracks.summary import *
from galaxy.datatypes.tabular import Vcf
from galaxy.datatypes.interval import Bed, Gff
from pysam import csamtools

MAX_VALS = 5000 # only display first MAX_VALS features

class TracksDataProvider( object ):
    """ Base class for tracks data providers. """
    
    """ 
    Mapping from column name to index in data. This mapping is used to create
    filters.
    """
    col_name_data_index_mapping = {}
    
    def __init__( self, converted_dataset=None, original_dataset=None ):
        """ Create basic data provider. """
        self.converted_dataset = converted_dataset
        self.original_dataset = original_dataset
        
    def get_data( self, chrom, start, end, **kwargs ):
        """ Returns data in region defined by chrom, start, and end. """
        # Override.
        pass
        
    def get_filters( self ):
        """ 
        Returns filters for provider's data. Return value is a list of 
        filters; each filter is a dictionary with the keys 'name', 'index', 'value'.
        NOTE: This method uses the original dataset's datatype and metadata to 
        create the filters.
        """
        # Get column names.
        try:
            column_names = self.original_dataset.datatype.column_names
        except AttributeError:
            column_names = range( self.original_dataset.metadata.columns )
            
        # Dataset must have column types; if not, cannot create filters.
        try:
            column_types = self.original_dataset.metadata.column_types
        except AttributeError:
            return []
            
        # Create and return filters.
        filters = []
        if self.original_dataset.metadata.viz_filter_columns:
            for viz_col_index in self.original_dataset.metadata.viz_filter_columns:
                col_name = column_names[ viz_col_index ]
                # Make sure that column has a mapped index. If not, do not add filter.
                try:
                    index = self.col_name_data_index_mapping[ col_name ]
                except KeyError:
                    continue
                filters.append(
                    { 'name' : col_name, 'value' : column_types[viz_col_index], \
                    'index' : index } )
        return filters
            
class SummaryTreeDataProvider( TracksDataProvider ):
    """
    Summary tree data provider for the Galaxy track browser. 
    """
    
    CACHE = LRUCache(20) # Store 20 recently accessed indices for performance
    
    def get_summary( self, chrom, start, end, **kwargs):
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

        level = ceil( log( resolution, st.block_size ) )
        level = int(max( level, 0 ))
        if level <= 0:
            return None

        stats = st.chrom_stats[chrom]
        results = st.query(chrom, int(start), int(end), level)
        if results == "detail":
            return None
        elif results == "draw" or level <= 1:
            return "no_detail"
        else:
            return results, stats[level]["max"], stats[level]["avg"], stats[level]["delta"]

class VcfDataProvider( TracksDataProvider ):
    """
    VCF data provider for the Galaxy track browser.

    Payload format: 
    [ uid (offset), start, end, ID, reference base(s), alternate base(s), quality score]
    """

    col_name_data_index_mapping = { 'Qual' : 6 }

    def get_data( self, chrom, start, end, **kwargs ):
        """ Returns data in region defined by chrom, start, and end. """
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

        for start, end, offset in index.find(chrom, start, end):
            if count >= MAX_VALS:
                message = "Only the first %s features are being displayed." % MAX_VALS
                break
            count += 1
            source.seek(offset)
            feature = source.readline().split()

            payload = [ offset, start, end, \
                        # ID: 
                        feature[2], \
                        # reference base(s):
                        feature[3], \
                        # alternative base(s)
                        feature[4], \
                        # phred quality score
                        feature[5] ]
            results.append(payload)

        return { 'data_type' : 'vcf', 'data': results, 'message': message }
                
class BamDataProvider( TracksDataProvider ):
    """
    Provides access to intervals from a sorted indexed BAM file.
    """        
    def get_data( self, chrom, start, end, **kwargs ):
        """
        Fetch intervals in the region 
        """
        start, end = int(start), int(end)
        # Attempt to open the BAM file with index
        bamfile = csamtools.Samfile( filename=self.original_dataset.file_name, mode='rb', index_filename=self.converted_dataset.file_name )
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
        # Encode reads as list of dictionaries
        results = []
        paired_pending = {}
        for read in data:
            if len(results) > MAX_VALS:
                message = "Only the first %s pairs are being displayed." % MAX_VALS
                break
            qname = read.qname
            if read.is_proper_pair:
                if qname in paired_pending: # one in dict is always first
                    pair = paired_pending[qname]
                    results.append( [ qname, pair['start'], read.pos + read.rlen, read.seq, [pair['start'], pair['end'], pair['seq']], [read.pos, read.pos + read.rlen, read.seq] ] )
                    # results.append( [read.qname, pair['start'], read.pos + read.rlen, qname, [pair['start'], pair['end']], [read.pos, read.pos + read.rlen] ] )
                    del paired_pending[qname]
                else:
                    paired_pending[qname] = { 'start': read.pos, 'end': read.pos + read.rlen, 'seq': read.seq, 'mate_start': read.mpos, 'rlen': read.rlen }
            else:
                results.append( [qname, read.pos, read.pos + read.rlen, read.seq] )
        # take care of reads whose mates are out of range
        for qname, read in paired_pending.iteritems():
            if read['mate_start'] < read['start']:
                start = read['mate_start']
                end = read['end']
                r1 = [read['mate_start'], read['mate_start']  + read['rlen']]
                r2 = [read['start'], read['end'], read['seq']]
            else:
                start = read['start']
                end = read['mate_start'] + read['rlen']
                r1 = [read['start'], read['end'], read['seq']]
                r2 = [read['mate_start'], read['mate_start'] + read['rlen']]

            results.append( [ qname, start, end, read['seq'], r1, r2 ] )

        bamfile.close()
        return { 'data': results, 'message': message }

class ArrayTreeDataProvider( TracksDataProvider ):
    """
    Array tree data provider for the Galaxy track browser. 
    """
    def get_stats( self, chrom ):
        f = open( self.converted_dataset.file_name )
        d = FileArrayTreeDict( f )
        try:
            chrom_array_tree = d[chrom]
        except KeyError:
            f.close()
            return None

        root_summary = chrom_array_tree.get_summary( 0, chrom_array_tree.levels )

        level = chrom_array_tree.levels - 1
        desired_summary = chrom_array_tree.get_summary( 0, level )
        bs = chrom_array_tree.block_size ** level

        frequencies = map(int, desired_summary.frequencies)
        out = [ (i * bs, freq) for i, freq in enumerate(frequencies) ]

        f.close()
        return {    'max': float( max(root_summary.maxs) ), \
                    'min': float( min(root_summary.mins) ), \
                    'frequencies': out, \
                    'total_frequency': sum(root_summary.frequencies) }

    # Return None instead of NaN to pass jQuery 1.4's strict JSON
    def float_nan(self, n):
        if n != n: # NaN != NaN
            return None
        else:
            return float(n)            

    def get_data( self, chrom, start, end, **kwargs ):
        if 'stats' in kwargs:
            return self.get_stats(chrom)

        f = open( self.converted_dataset.file_name )
        d = FileArrayTreeDict( f )

        # Get the right chromosome
        try:
            chrom_array_tree = d[chrom]
        except:
            f.close()
            return None

        block_size = chrom_array_tree.block_size
        start = int( start )
        end = int( end )
        resolution = max(1, ceil(float(kwargs['resolution'])))

        level = int( floor( log( resolution, block_size ) ) )
        level = max( level, 0 )
        stepsize = block_size ** level

        # Is the requested level valid?
        assert 0 <= level <= chrom_array_tree.levels

        results = []
        for block_start in range( start, end, stepsize * block_size ):
            # print block_start
            # Return either data point or a summary depending on the level
            indexes = range( block_start, block_start + stepsize * block_size, stepsize )
            if level > 0:
                s = chrom_array_tree.get_summary( block_start, level )
                if s is not None:
                    results.extend( zip( indexes, map( self.float_nan, s.sums / s.counts ) ) )
            else:
                l = chrom_array_tree.get_leaf( block_start )
                if l is not None:
                    results.extend( zip( indexes, map( self.float_nan, l ) ) )

        f.close()
        return results

class IntervalIndexDataProvider( TracksDataProvider ):
    """
    Interval index data provider for the Galaxy track browser.
    
    Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
    """
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

        for start, end, offset in index.find(chrom, start, end):
            if count >= MAX_VALS:
                message = "Only the first %s features are being displayed." % MAX_VALS
                break
            count += 1
            source.seek(offset)
            feature = source.readline().split()
            payload = [ offset, start, end ]
            # TODO: can we use column metadata to fill out payload?
            # TODO: use function to set payload data
            if "no_detail" not in kwargs:
                length = len(feature)
                if isinstance( self.original_dataset.datatype, Gff ):
                    # GFF dataset.
                    if length >= 3:
                        payload.append( feature[2] ) # name
                    if length >= 7:
                        payload.append( feature[6] ) # strand
                elif isinstance( self.original_dataset.datatype, Bed ):
                    # BED dataset.
                    if length >= 4:
                        payload.append(feature[3]) # name
                    if length >= 6: # strand
                        payload.append(feature[5])

                    if length >= 8:
                        payload.append(int(feature[6]))
                        payload.append(int(feature[7]))

                    if length >= 12:
                        block_sizes = [ int(n) for n in feature[10].split(',') if n != '']
                        block_starts = [ int(n) for n in feature[11].split(',') if n != '' ]
                        blocks = zip(block_sizes, block_starts)
                        payload.append( [ (start + block[1], start + block[1] + block[0]) for block in blocks] )

            results.append(payload)

        return { 'data': results, 'message': message }
        
#        
# Helper methods.
#

# Mapping from dataset type name to a class that can fetch data from a file of that
# type. First key is converted dataset type; if result is another dict, second key
# is original dataset type. TODO: This needs to be more flexible.
dataset_type_name_to_data_provider = {
    "array_tree": ArrayTreeDataProvider,
    "interval_index": { "vcf": VcfDataProvider, "default" : IntervalIndexDataProvider },
    "bai": BamDataProvider,
    "summary_tree": SummaryTreeDataProvider
}

dataset_type_to_data_provider = {
    Vcf : VcfDataProvider
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
            data_provider = value.get( original_dataset.ext, value.get( "default" ) )
        else:
            data_provider = value
    elif original_dataset:
        # Look for data provider in mapping.
        data_provider = \
            dataset_type_to_data_provider.get( original_dataset.datatype.__class__, None )
        
        # If get_track_type is available, then dataset can be added to trackster 
        # and hence has at least a generic data provider.
        try:
            original_dataset.datatype.get_track_type()
            data_provider = TracksDataProvider
        except:
            pass
    return data_provider

