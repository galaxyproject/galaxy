'''
Summary tree data structure for feature aggregation across large genomic regions.
'''

import sys, os
import cPickle

# TODO: What are the performance implications of setting min level to 1? Data
# structure size and/or query speed? It would be nice to have level 1 data
# so that client does not have to compute it.
MIN_LEVEL = 2

class SummaryTree:
    def __init__( self, block_size=25, levels=6, draw_cutoff=150, detail_cutoff=30 ):
        self.chrom_blocks = {}
        self.levels = levels
        self.draw_cutoff = draw_cutoff
        self.detail_cutoff = detail_cutoff
        self.block_size = block_size
        self.chrom_stats = {}
    
    def find_block( self, num, level ):
        """ Returns block that num is in for level. """
        return ( num / self.block_size ** level )
        
    def insert_range( self, chrom, start, end ):
        """ Inserts a feature at chrom:start-end into the tree. """
        
        # Get or set up chrom blocks.
        if chrom in self.chrom_blocks:
            blocks = self.chrom_blocks[ chrom ]
        else:
            blocks = self.chrom_blocks[ chrom ] = {}
            self.chrom_stats[ chrom ] = {}
            for level in range( MIN_LEVEL, self.levels + 1 ):
                blocks[ level ] = {}
            
        # Insert feature into all matching blocks at all levels.
        for level in range( MIN_LEVEL, self.levels + 1 ):
            block_level = blocks[ level ]
            starting_block = self.find_block( start, level )
            ending_block = self.find_block( end, level )
            for block in range( starting_block, ending_block + 1 ):
                if block in block_level:
                    block_level[ block ] += 1
                else:
                    block_level[ block ] = 1
        
    def finish( self ):
        """ Compute stats for levels. """
        
        for chrom, blocks in self.chrom_blocks.iteritems():
            for level in range( self.levels, MIN_LEVEL - 1, -1 ):
                # Set level's stats.
                max_val = max( blocks[ level ].values() )
                self.chrom_stats[ chrom ][ level ] = {}
                self.chrom_stats[ chrom ][ level ][ "delta" ] = self.block_size ** level
                self.chrom_stats[ chrom ][ level ][ "max" ] = max_val
                self.chrom_stats[ chrom ][ level ][ "avg" ] = float( max_val ) / len( blocks[ level ] )
            
            self.chrom_blocks[ chrom ] = dict( [ ( key, value ) for key, value in blocks.iteritems() ] )
        
    def query( self, chrom, start, end, level, draw_cutoff=None, detail_cutoff=None ):
        """ Queries tree for data. """

        # Set cutoffs to self's attributes if not defined.
        if draw_cutoff != 0:
            draw_cutoff = self.draw_cutoff
        if detail_cutoff != 0:
            detail_cutoff = self.detail_cutoff

        # Get data.
        if chrom in self.chrom_blocks:
            stats = self.chrom_stats[ chrom ]

            # For backwards compatibility:
            if "detail_level" in stats and level <= stats[ "detail_level" ]:
                return "detail"
            elif "draw_level" in stats and level <= stats[ "draw_level" ]:
                return "draw"

            # If below draw, detail level, return string to denote this.
            max = stats[ level ][ "max" ]
            if max < detail_cutoff:
                return "detail"
            if max < draw_cutoff:
                return "draw"
            
            # Return block data.
            blocks = self.chrom_blocks[ chrom ]
            results = []
            multiplier = self.block_size ** level
            starting_block = self.find_block( start, level )
            ending_block = self.find_block( end, level )
            for block in range( starting_block, ending_block + 1 ):
                val = 0
                if block in blocks[ level ]:
                    val = blocks[ level ][ block ]
                results.append(  ( block * multiplier, val )  )
            return results
            
        return None
        
    def write( self, filename ):
        """ Writes tree to file. """
        self.finish()
        cPickle.dump( self, open( filename, 'wb' ), 2 )
        
def summary_tree_from_file( filename ):
    return cPickle.load( open( filename, "rb" ) )
    
