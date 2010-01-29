"""
Visualization data provider for BAM format.
"""

import pkg_resources; pkg_resources.require( "pysam" )

from pysam import csamtools
from math import floor, ceil, log
import logging
# log = logging.getLogger(__name__)

class BamDataProvider( object ):
    """
    Provides access to intervals from a sorted indexed BAM file.
    """
    def __init__( self, index, original_dataset ):
        
        self.index = index
        self.original_dataset = original_dataset
        
    def get_data( self, chrom, start, end, **kwargs ):
        """
        Fetch intervals in the region 
        """
        start, end = int(start), int(end)
        # Attempt to open the BAM file with index
        bamfile = csamtools.Samfile( filename=self.original_dataset.file_name, mode='rb', index_filename=self.index.file_name )
        try:
            data = bamfile.fetch(start=start, end=end, reference=chrom)
        except ValueError, e:
            # Some BAM files do not prefix chromosome names with chr, try without
            if chrom.startswith( 'chr' ):
                data = bamfile.fetch( start=start, end=end, reference=chrom[3:] )
            else:
                raise
        # Encode reads as list of dictionaries
        results = []
        for read in data:
            payload = { 'uid': str(read.pos) + str(read.seq), 'start': read.pos, 'end': read.pos + read.rlen, 'name': read.seq }
            results.append(payload)
        bamfile.close()
        return results
            