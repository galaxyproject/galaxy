"""
Array tree data provider for the Galaxy track browser. 
"""

import pkg_resources
pkg_resources.require( "numpy" )
pkg_resources.require( "bx-python" )
from bx.arrays.array_tree import FileArrayTreeDict
from math import floor, ceil, log, pow
from base import TracksDataProvider

class ArrayTreeDataProvider( TracksDataProvider ):
    def __init__( self, dataset, original_dataset ):
        self.dataset = dataset
        
    def get_stats( self, chrom ):
        f = open( self.dataset.file_name )
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
            
        f = open( self.dataset.file_name )
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
