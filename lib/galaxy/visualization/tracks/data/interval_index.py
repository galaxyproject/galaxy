"""
Interval index data provider for the Galaxy track browser.
Kanwei Li, 2010

Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
"""

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.interval_index_file import Indexes
from galaxy.datatypes.interval import Bed, Gff
from galaxy.datatypes.tabular import Vcf

MAX_VALS = 5000 # only display first MAX_VALS features

class IntervalIndexDataProvider( object ):
    def __init__( self, converted_dataset, original_dataset ):
        self.original_dataset = original_dataset
        self.converted_dataset = converted_dataset
    
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
                elif isinstance( self.original_dataset.datatype, Vcf ):
                    # VCF dataset.
                    payload.append( feature[2] ) # name
                    
            results.append(payload)
        
        return { 'data': results, 'message': message }
