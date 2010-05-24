#Dan Blankenberg
import string
from optparse import OptionParser
from galaxy_utils.sequence.fastq import fastqReader, fastqWriter


def get_score_comparer( operator ):
    if operator == 'gt':
        return compare_gt
    elif operator == 'ge':
        return compare_ge
    elif operator == 'eq':
        return compare_eq
    elif operator == 'lt':
        return compare_lt
    elif operator == 'le':
        return compare_le
    elif operator == 'ne':
        return compare_ne
    raise 'Invalid operator provided: %s' % operator

def compare_gt( quality_score, threshold_value ):
    return quality_score > threshold_value

def compare_ge( quality_score, threshold_value ):
    return quality_score >= threshold_value

def compare_eq( quality_score, threshold_value ):
    return quality_score == threshold_value

def compare_ne( quality_score, threshold_value ):
    return quality_score != threshold_value

def compare_lt( quality_score, threshold_value ):
    return quality_score < threshold_value

def compare_le( quality_score, threshold_value ):
    return quality_score <= threshold_value

class BaseReplacer( object ):
    def __init__( self, replace_character ):
        self.replace_character = replace_character
    def __call__( self, base_character ):
        return self.replace_character

def main():
    usage = "usage: %prog [options] input_file output_file"
    parser = OptionParser( usage=usage )
    parser.add_option( '-f', '--format', dest='format', type='choice', default='sanger', choices=( 'sanger', 'solexa', 'illumina' ), help='FASTQ variant type' )
    parser.add_option( '-m', '--mask_character', dest='mask_character', default='N', help='Mask Character to use' )
    parser.add_option( '-c', '--score_comparison', type="choice", dest='score_comparison', default='le', choices=('gt','ge','eq','lt', 'le', 'ne' ), help='Mask base when score is' )
    parser.add_option( '-s', '--quality_score', type="float", dest='quality_score', default='0', help='Quality Score' )
    parser.add_option( "-l", "--lowercase", action="store_true", dest="lowercase", default=False, help="Use lowercase masking")
    ( options, args ) = parser.parse_args()
    
    if len ( args ) != 2:
        parser.error( "Need to specify an input file and an output file" )
    
    score_comparer = get_score_comparer( options.score_comparison )
    
    if options.lowercase:
        base_masker = string.lower
    else:
        base_masker = BaseReplacer( options.mask_character )
    
    out = fastqWriter( open( args[1], 'wb' ), format = options.format )
    
    num_reads = None
    num_reads_excluded = 0
    for num_reads, fastq_read in enumerate( fastqReader( open( args[0] ), format = options.format ) ):
        sequence_list = list( fastq_read.sequence )
        for i, quality_score in enumerate( fastq_read.get_decimal_quality_scores() ):
            if score_comparer( quality_score, options.quality_score ):
                sequence_list[ i ] = base_masker( sequence_list[ i ] )
        fastq_read.sequence = "".join( sequence_list )
        out.write( fastq_read )
    
    if num_reads is not None:
        print "Processed %i %s reads." % ( num_reads + 1, options.format )
    else:
        print "No valid FASTQ reads were provided."

if __name__ == "__main__": main()
