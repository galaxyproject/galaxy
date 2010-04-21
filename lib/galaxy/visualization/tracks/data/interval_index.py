"""
Interval index data provider for the Galaxy track browser.
Kanwei Li, 2010

Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
"""

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.interval_index_file import Indexes

class IntervalIndexDataProvider( object ):
    def __init__( self, converted_dataset, original_dataset ):
        self.original_dataset = original_dataset
        self.converted_dataset = converted_dataset
    
    def get_data( self, chrom, start, end, **kwargs ):
        start, end = int(start), int(end)
        chrom = str(chrom)
        source = open( self.original_dataset.file_name )
        index = Indexes( self.converted_dataset.file_name )
        results = []
        
        for start, end, offset in index.find(chrom, start, end):
            source.seek(offset)
            feature = source.readline().split()
            payload = [ offset, start, end ]
            if "no_detail" not in kwargs:
                length = len(feature)
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
        
        return results
