import pkg_resources; pkg_resources.require( "bx-python" )
from bx.interval_index_file import Indexes
from galaxy.datatypes.tabular import Vcf
from base import TracksDataProvider

MAX_VALS = 5000 # only display first MAX_VALS features

class VcfDataProvider( TracksDataProvider ):
    """
    VCF data provider for the Galaxy track browser.

    Payload format: 
    [ uid (offset), start, end, ID, reference base(s), alternate base(s), quality score]
    """
    
    col_name_data_index_mapping = { 'Qual' : 6 }
    
    def get_data( self, chrom, start, end, **kwargs ):
        """ Returns data in region defined by chrom, start, and end. """
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
            
            payload = [ offset, start, end, \
                        # ID: 
                        feature[2], \
                        # reference base(s):
                        feature[3], \
                        # alternative base(s)
                        feature[4], \
                        # phred quality score
                        feature[5] ]
            results.append(payload)
        
        return { 'data_type' : 'vcf', 'data': results, 'message': message }
