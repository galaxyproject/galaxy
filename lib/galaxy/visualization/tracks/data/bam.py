import pkg_resources; pkg_resources.require( "pysam" )
from pysam import csamtools
from math import floor, ceil, log
import logging

class BamDataProvider( object ):
    def __init__( self, index, original_dataset ):
        self.log = logging.getLogger(__name__)
        self.index = index
        self.original_dataset = original_dataset
        
    def get_data( self, chrom, start, end, **kwargs ):
        start, end = int(start), int(end)
        bamfile = csamtools.Samfile(filename=self.original_dataset.file_name, mode='rb', index_filename=self.index.file_name)
        
        data = bamfile.fetch(start=start, end=end, reference=chrom)
        results = []
        for read in data:
            payload = { 'uid': str(read.pos) + str(read.seq), 'start': read.pos, 'end': read.pos + read.rlen, 'name': read.seq }
            
            results.append(payload)
        bamfile.close()
        return results
            