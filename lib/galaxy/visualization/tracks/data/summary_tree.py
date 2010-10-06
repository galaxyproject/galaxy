"""
Summary tree data provider for the Galaxy track browser. 
"""

import pkg_resources; pkg_resources.require( "bx-python" )
from galaxy.visualization.tracks.summary import *
from math import ceil, log
from galaxy.util.lrucache import LRUCache

CACHE = LRUCache(20) # Store 20 recently accessed indices for performance

class SummaryTreeDataProvider( object ):
    def __init__( self, dataset, original_dataset ):
        self.dataset = dataset
        
    def get_summary( self, chrom, start, end, **kwargs):
        filename = self.dataset.file_name
        st = CACHE[filename]
        if st is None:
            st = summary_tree_from_file( self.dataset.file_name )
            CACHE[filename] = st
            
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
