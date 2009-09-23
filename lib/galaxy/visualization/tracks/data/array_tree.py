"""
Array tree data provider for Galaxy track browser. 
"""

import pkg_resources; pkg_resources.require( "bx-python" )
try:
    from bx.arrays.array_tree import FileArrayTreeDict
except:
    pass
from math import floor, ceil, log

# Maybe this should be included in the datatype itself, so users can add their
# own types to the browser as long as they return the right format of data?

# FIXME: Assuming block size is always 1000 for the moment
BLOCK_SIZE = 1000

class ArrayTreeDataProvider( object ):
    def __init__( self, dataset ):
        self.dataset = dataset
    
    def get_stats( self, chrom ):
        d = FileArrayTreeDict( open( self.dataset.file_name ) )
        try:
            chrom_array_tree = d[chrom]
        except KeyError:
            return None
        
        root_summary = chrom_array_tree.get_summary( 0, chrom_array_tree.levels )
        return { 'max': float( max(root_summary.maxs) ), 'min': float( min(root_summary.mins) ) }
    
    def get_data( self, chrom, start, end ):
        start = int( start )
        end = int( end )
        level = int( ceil( log( end - start, BLOCK_SIZE ) ) ) - 1
        print "!!!!", start, end,  level
        # Open the file
        print self.dataset.file_name
        d = FileArrayTreeDict( open( self.dataset.file_name ) )
        # Get the right chromosome
        try:
            chrom_array_tree = d[chrom]
        except KeyError:
            return None
        # Is the requested level valid?
        assert 0 <= level <= chrom_array_tree.levels
        # Calculate the actual start/range/step of the block we're getting
        size = BLOCK_SIZE ** (level+1)
        block_start = ( start // BLOCK_SIZE ) * BLOCK_SIZE
        block_step = size // BLOCK_SIZE
        indexes = range( block_start, block_start + size, block_step )
        # Return either data point or a summary depending on the level
        if level > 0:
            s = chrom_array_tree.get_summary( start, level )
            if s is not None:
                return zip( indexes,  map( float, s.sums / s.counts ) )
            else:
                return None
        else:
            v = chrom_array_tree.get_leaf( start )
            if v is not None:
                return zip( indexes, map( float, v ) )
            else:
                return None