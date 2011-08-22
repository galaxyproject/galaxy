#Dan Blankenberg
import sys
from galaxy_utils.sequence.fastq import fastqReader, fastqVerboseErrorReader, fastqAggregator, fastqWriter

def main():
    input_filename = sys.argv[1]
    input_type = sys.argv[2]
    output_filename = sys.argv[3]
    output_type = sys.argv[4]
    force_quality_encoding = sys.argv[5]
    summarize_input = sys.argv[6] == 'summarize_input'
    if force_quality_encoding == 'None':
        force_quality_encoding = None
    
    aggregator = fastqAggregator()
    out = fastqWriter( open( output_filename, 'wb' ), format = output_type, force_quality_encoding = force_quality_encoding )
    read_count = None
    if summarize_input:
        reader = fastqVerboseErrorReader
    else:
        reader = fastqReader
    for read_count, fastq_read in enumerate( reader( open( input_filename ), format = input_type, apply_galaxy_conventions = True ) ):
        if summarize_input:
            aggregator.consume_read( fastq_read )
        out.write( fastq_read )
    out.close()
    
    if read_count is not None:
        print "Groomed %i %s reads into %s reads." % ( read_count + 1, input_type, output_type )
        if input_type != output_type and 'solexa' in [ input_type, output_type ]:
            print "Converted between Solexa and PHRED scores."
        if summarize_input:
            print "Based upon quality and sequence, the input data is valid for: %s" % ( ", ".join( aggregator.get_valid_formats() )  or "None" )
            ascii_range = aggregator.get_ascii_range()
            decimal_range =  aggregator.get_decimal_range()
            print "Input ASCII range: %s(%i) - %s(%i)" % ( repr( ascii_range[0] ), ord( ascii_range[0] ), repr( ascii_range[1] ), ord( ascii_range[1] ) ) #print using repr, since \x00 (null) causes info truncation in galaxy when printed
            print "Input decimal range: %i - %i" % ( decimal_range[0], decimal_range[1] )        
    else:
        print "No valid FASTQ reads were provided."


if __name__ == "__main__": main()
