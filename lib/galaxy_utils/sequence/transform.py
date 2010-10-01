#Dan Blankenberg
#Contains methods to tranform sequence strings
import string

#Translation table for reverse Complement, with ambiguity codes
DNA_COMPLEMENT = string.maketrans( "ACGTRYKMBDHVacgtrykmbdhv", "TGCAYRMKVHDBtgcayrmkvhdb" )
RNA_COMPLEMENT = string.maketrans( "ACGURYKMBDHVacgurykmbdhv", "UGCAYRMKVHDBugcayrmkvhdb" )
#Translation table for DNA <--> RNA
DNA_TO_RNA = string.maketrans( "Tt", "Uu" )
RNA_TO_DNA = string.maketrans( "Uu", "Tt" )

#reverse sequence string
def reverse( sequence ):
    return sequence[::-1]
#complement DNA sequence string
def DNA_complement( sequence ):
    return sequence.translate( DNA_COMPLEMENT )
#complement RNA sequence string
def RNA_complement( sequence ):
    return sequence.translate( RNA_COMPLEMENT )
#returns the reverse complement of the sequence
def DNA_reverse_complement( sequence ):
    sequence = reverse( sequence )
    return DNA_complement( sequence )
def RNA_reverse_complement( sequence ):
    sequence = reverse( sequence )
    return RNA_complement( sequence )
def to_DNA( sequence ):
    return sequence.translate( DNA_TO_RNA )
def to_RNA( sequence ):
    return sequence.translate( RNA_TO_DNA )

class ColorSpaceConverter( object ):
    unknown_base = 'N'
    unknown_color = '.'
    color_to_base_dict = {}
    color_to_base_dict[ 'A' ] = { '0':'A', '1':'C', '2':'G', '3':'T', '4':'N', '5':'N', '6':'N', '.':'N' }
    color_to_base_dict[ 'C' ] = { '0':'C', '1':'A', '2':'T', '3':'G', '4':'N', '5':'N', '6':'N', '.':'N' }
    color_to_base_dict[ 'G' ] = { '0':'G', '1':'T', '2':'A', '3':'C', '4':'N', '5':'N', '6':'N', '.':'N' }
    color_to_base_dict[ 'T' ] = { '0':'T', '1':'G', '2':'C', '3':'A', '4':'N', '5':'N', '6':'N', '.':'N' }
    color_to_base_dict[ 'N' ] = { '0':'N', '1':'N', '2':'N', '3':'N', '4':'N', '5':'N', '6':'N', '.':'N' }
    base_to_color_dict = {}
    for base, color_dict in color_to_base_dict.iteritems():
        base_to_color_dict[ base ] = {}
        for key, value in color_dict.iteritems():
            base_to_color_dict[ base ][ value ] = key
        base_to_color_dict[ base ][ 'N' ] = '4' #force ACGT followed by N to be '4', because this is now 'processed' data; we could force to '.' (non-processed data) also
    base_to_color_dict[ 'N' ].update( { 'A':'5', 'C':'5', 'G':'5', 'T':'5', 'N':'6' } )
    def __init__( self, fake_adapter_base = 'G' ):
        assert fake_adapter_base in self.base_to_color_dict, 'A bad fake adapter base was provided: %s.' % fake_adapter_base
        self.fake_adapter_base = fake_adapter_base
    def to_color_space( self, sequence, adapter_base = None ):
        if adapter_base is None:
            adapter_base = self.fake_adapter_base
        last_base = adapter_base #we add a fake adapter base so that the sequence can be decoded properly again
        rval = last_base
        for base in sequence:
            rval += self.base_to_color_dict.get( last_base, self.base_to_color_dict[ self.unknown_base ] ).get( base, self.unknown_color )
            last_base = base
        return rval
    def to_base_space( self, sequence ):
        if not isinstance( sequence, list ):
            sequence = list( sequence )
        if sequence:
            last_base = sequence.pop( 0 )
        else:
            last_base = None
        assert last_base in self.color_to_base_dict, 'A valid adapter base must be included when converting to base space from color space. Found: %s' % last_base
        rval = ''
        for color_val in sequence:
            last_base = self.color_to_base_dict[ last_base ].get( color_val, self.unknown_base )
            rval += last_base
        return rval
