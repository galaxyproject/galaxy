"""
Visualization data provider for BAM format.
Kanwei Li, 2010
"""

import pkg_resources; pkg_resources.require( "pysam" )

from pysam import csamtools
from math import floor, ceil, log
import logging
log = logging.getLogger(__name__)

MAX_VALS = 5000 # only display first MAX_VALS datapoints

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
        message = None
        try:
            data = bamfile.fetch(start=start, end=end, reference=chrom)
        except ValueError, e:
            # Some BAM files do not prefix chromosome names with chr, try without
            if chrom.startswith( 'chr' ):
                try:
                    data = bamfile.fetch( start=start, end=end, reference=chrom[3:] )
                except ValueError:
                    return None
            else:
                return None
        # Encode reads as list of dictionaries
        results = []
        paired_pending = {}
        for read in data:
            if len(results) > MAX_VALS:
                message = "Only the first %s pairs are being displayed." % MAX_VALS
                break
            qname = read.qname
            if read.is_proper_pair:
                if qname in paired_pending: # one in dict is always first
                    pair = paired_pending[qname]
                    results.append( [ qname, pair['start'], read.pos + read.rlen, read.seq, [pair['start'], pair['end'], pair['seq']], [read.pos, read.pos + read.rlen, read.seq] ] )
                    # results.append( [read.qname, pair['start'], read.pos + read.rlen, qname, [pair['start'], pair['end']], [read.pos, read.pos + read.rlen] ] )
                    del paired_pending[qname]
                else:
                    paired_pending[qname] = { 'start': read.pos, 'end': read.pos + read.rlen, 'seq': read.seq, 'mate_start': read.mpos, 'rlen': read.rlen }
            else:
                results.append( [qname, read.pos, read.pos + read.rlen, read.seq] )
        # take care of reads whose mates are out of range
        for qname, read in paired_pending.iteritems():
            if read['mate_start'] < read['start']:
                start = read['mate_start']
                end = read['end']
                r1 = [read['mate_start'], read['mate_start']  + read['rlen']]
                r2 = [read['start'], read['end'], read['seq']]
            else:
                start = read['start']
                end = read['mate_start'] + read['rlen']
                r1 = [read['start'], read['end'], read['seq']]
                r2 = [read['mate_start'], read['mate_start'] + read['rlen']]

            results.append( [ qname, start, end, read['seq'], r1, r2 ] )
            
        bamfile.close()
        return { 'data': results, 'message': message }
