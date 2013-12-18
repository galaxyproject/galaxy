#Dan Blankenberg
import sys, os, shutil
from galaxy_utils.sequence.fastq import fastqReader, fastqNamedReader, fastqWriter, fastqJoiner

def main():
    #Read command line arguments
    input1_filename = sys.argv[1]
    input1_type = sys.argv[2] or 'sanger'
    input2_filename = sys.argv[3]
    input2_type = sys.argv[4] or 'sanger'
    output_filename = sys.argv[5]
    
    if input1_type != input2_type:
        print "WARNING: You are trying to join files of two different types: %s and %s." % ( input1_type, input2_type )
    
    input2 = fastqNamedReader( open( input2_filename, 'rb' ), input2_type )
    joiner = fastqJoiner( input1_type )
    out = fastqWriter( open( output_filename, 'wb' ), format = input1_type )
    
    i = None
    skip_count = 0
    for i, fastq_read in enumerate( fastqReader( open( input1_filename, 'rb' ), format = input1_type ) ):
        identifier = joiner.get_paired_identifier( fastq_read )
        fastq_paired = input2.get( identifier )
        if fastq_paired is None:
            skip_count += 1
        else:
            out.write( joiner.join( fastq_read, fastq_paired ) )
    out.close()
    
    if i is None:
        print "Your file contains no valid FASTQ reads."
    else:
        print input2.has_data()
        print 'Joined %s of %s read pairs (%.2f%%).' % ( i - skip_count + 1, i + 1, float( i - skip_count + 1 ) / float( i + 1 ) * 100.0 )

if __name__ == "__main__":
    main()
