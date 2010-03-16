"""
Array tree data provider for the Galaxy track browser. 
"""

import pkg_resources; pkg_resources.require( "bx-python" )
try:
    from bx.arrays.array_tree import FileArrayTreeDict
except:
    pass
from math import floor, ceil, log, pow
import logging
logger = logging.getLogger(__name__)

# Maybe this should be included in the datatype itself, so users can add their
# own types to the browser as long as they return the right format of data?

SUMMARIZE_N = 200

class ArrayTreeDataProvider( object ):
    def __init__( self, dataset, original_dataset ):
        self.dataset = dataset
        
    # def calc_resolution(self, start, end, density):
        # return pow( 10, ceil( log( (end - start) / density , 10 ) ) )
    
    def get_stats( self, chrom ):
        f = open( self.dataset.file_name )
        d = FileArrayTreeDict( f )
        try:
            chrom_array_tree = d[chrom]
        except KeyError:
            f.close()
            return "no data"
        
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
        f = open( self.dataset.file_name )
        d = FileArrayTreeDict( f )
        
        # Get the right chromosome
        try:
            chrom_array_tree = d[chrom]
        except KeyError:
            f.close()
            return None
        
        block_size = chrom_array_tree.block_size
        start = int( start )
        end = int( end )
        resolution = max(1, ceil(float(kwargs['resolution'])))
        
        level = int( ceil( log( resolution, block_size ) ) )
        level = max( level, 0 )
        stepsize = block_size ** level
        
        # Is the requested level valid?
        assert 0 <= level <= chrom_array_tree.levels
        
        if "frequencies" in kwargs:
            if level <= 0:
                # Low level enough to always display features
                f.close()
                return None
            else:
                # Round to nearest bin
                bin_start = start // (stepsize * block_size) * (stepsize * block_size)
                
                indexes = range( bin_start, (bin_start + stepsize * block_size), stepsize )
                summary = chrom_array_tree.get_summary( bin_start, level )
                if summary:
                    results = zip( indexes, map( int, summary.frequencies ) )
                    filtered = filter(lambda tup: tup[0] >= start and tup[0] <= end, results)
                    sums = 0
                    max_f = 0
                    for tup in filtered:
                        sums += tup[1]
                        max_f = max(max_f, tup[1])                    
                    
                    if max_f > 10000:
                        f.close()
                        return filtered, int(sums), float(sums)/len(filtered)
                f.close()
                return None
            
        else:
            results = []
            for block_start in range( start, end, stepsize * block_size ):
                # print block_start
                # Return either data point or a summary depending on the level
                indexes = range( block_start, block_start + stepsize * block_size, stepsize )
                if level > 0:
                    s = chrom_array_tree.get_summary( block_start, level )
                    if s:
                        results.extend( zip( indexes, map( self.float_nan, s.sums / s.counts ) ) )
                else:
                    l = chrom_array_tree.get_leaf( block_start )
                    if l:
                        results.extend( zip( indexes, map( self.float_nan, l ) ) )
        
        f.close()
        return results
