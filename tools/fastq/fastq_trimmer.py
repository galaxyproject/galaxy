#Dan Blankenberg
import sys
from galaxy_utils.sequence.fastq import fastqReader, fastqWriter

def main():
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    left_offset = sys.argv[3]
    right_offset = sys.argv[4]
    percent_offsets = sys.argv[5] == 'offsets_percent'
    input_type = sys.argv[6] or 'sanger'
    keep_zero_length = sys.argv[7] == 'keep_zero_length'
    
    out = fastqWriter( open( output_filename, 'wb' ), format = input_type )
    num_reads_excluded = 0
    num_reads = None
    for num_reads, fastq_read in enumerate( fastqReader( open( input_filename ), format = input_type ) ):
        if percent_offsets:
            left_column_offset = int( round( float( left_offset ) / 100.0 * float( len( fastq_read ) ) ) )
            right_column_offset = int( round( float( right_offset ) / 100.0 * float( len( fastq_read ) ) ) )
        else:
            left_column_offset = int( left_offset )
            right_column_offset = int( right_offset )
        if right_column_offset > 0:
            right_column_offset = -right_column_offset
        else:
            right_column_offset = None
        fastq_read = fastq_read.slice( left_column_offset, right_column_offset )
        if keep_zero_length or len( fastq_read ):
            out.write( fastq_read )
        else:
            num_reads_excluded += 1
    out.close()
    if num_reads is None:
        print "No valid fastq reads could be processed."
    else:
        print "%i fastq reads were processed." % ( num_reads + 1 )
    if num_reads_excluded:
        print "%i reads of zero length were excluded from the output." % num_reads_excluded

if __name__ == "__main__": main()
