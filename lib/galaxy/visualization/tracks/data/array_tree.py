"""
Array tree data provider for the Galaxy track browser. 
"""

import pkg_resources; pkg_resources.require( "bx-python" )
try:
    from bx.arrays.array_tree import FileArrayTreeDict
except:
    pass
from math import floor, ceil, log

# Maybe this should be included in the datatype itself, so users can add their
# own types to the browser as long as they return the right format of data?

class ArrayTreeDataProvider( object ):
    def __init__( self, dataset, original_dataset ):
        self.dataset = dataset
    
    def get_stats( self, chrom ):
        f = open( self.dataset.file_name )
        d = FileArrayTreeDict( f )
        try:
            chrom_array_tree = d[chrom]
        except KeyError:
            f.close()
            return "no data"
        
        root_summary = chrom_array_tree.get_summary( 0, chrom_array_tree.levels )
        f.close()
        return { 'max': float( max(root_summary.maxs) ), 'min': float( min(root_summary.mins) ) }
    
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

        level = int( floor( log( resolution, block_size ) ) )
        level = max( level, 0 )
        stepsize = block_size ** level
        step1 = stepsize * block_size
        
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
                    results.extend( zip( indexes,  map( float, s.sums / s.counts ) ) )
            else:
                v = chrom_array_tree.get_leaf( block_start )
                if v is not None:
                    results.extend( zip( indexes, map( float, v ) ) )
        
        f.close()
        return results
