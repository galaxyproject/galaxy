"""
Interval index data provider for the Galaxy track browser.
Kanwei Li, 2009
"""

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.interval_index_file import Indexes

class IntervalIndexDataProvider( object ):
    def __init__( self, converted_dataset, original_dataset ):
        self.original_dataset = original_dataset
        self.converted_dataset = converted_dataset
    
    def get_data( self, chrom, start, end ):
        start, end = int(start), int(end)
        chrom = str(chrom)
        source = open( self.original_dataset.file_name )
        index = Indexes( self.converted_dataset.file_name )
        results = []
        
        for start, end, offset in index.find(chrom, start, end):
            source.seek(offset)
            feature = source.readline().split()
            payload = { 'start': start, 'end': end, 'name': feature[3], 'strand': feature[5] }
            try:
                block_sizes = [ int(n) for n in feature[10].split(',') if n != '']
                block_starts = [ int(n) for n in feature[11].split(',') if n != '' ]
                blocks = zip(block_sizes, block_starts)
                payload['blocks'] = [ (start + block[1], start + block[1] + block[0]) for block in blocks]
            except IndexError:
                pass
    
            try:
                payload['exon_start'] = int(feature[6])
                payload['exon_end'] = int(feature[7])
            except IndexError:
                pass

            results.append(payload)
        
        return results
