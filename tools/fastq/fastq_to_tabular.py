#Dan Blankenberg
import sys
from galaxy_utils.sequence.fastq import fastqReader

def main():
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    input_type = sys.argv[3] or 'sanger' #input type should ordinarily be unnecessary
    
    num_reads = None
    fastq_read = None
    out = open( output_filename, 'wb' )
    for num_reads, fastq_read in enumerate( fastqReader( open( input_filename ), format = input_type ) ):
        out.write( "%s\t%s\t%s\n" % ( fastq_read.identifier[1:].replace( '\t', ' ' ), fastq_read.sequence.replace( '\t', ' ' ), fastq_read.quality.replace( '\t', ' ' ) ) )
    out.close()
    if num_reads is None:
        print "No valid FASTQ reads could be processed."
    else:
        print "%i FASTQ reads were converted to Tabular." % ( num_reads + 1 )
    
if __name__ == "__main__": main()
