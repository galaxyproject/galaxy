#Florent Angly
import sys
from galaxy_utils.sequence.fastq import fastqReader, fastqWriter, fastqNamedReader, fastqJoiner

def main():
    mate1_filename  = sys.argv[1]
    mate1_type      = sys.argv[2] or 'sanger'
    mate2_filename  = sys.argv[3]
    mate2_type      = sys.argv[4] or 'sanger'
    output_filename = sys.argv[5]

    if mate1_type != mate2_type:
        print "WARNING: You are trying to interlace files of two different types: %s and %s." % ( mate1_type, mate2_type )
        return

    type = mate1_type
    joiner = fastqJoiner( type )
    out = fastqWriter( open( output_filename, 'wb' ), format = type )
    mate_input = fastqNamedReader( open( mate2_filename, 'rb' ), format = type  )

    i = None
    skip_count = 0
    for i, mate1 in enumerate( fastqReader( open( mate1_filename, 'rb' ), format = type ) ):

        mate2 = mate_input.get( joiner.get_paired_identifier( mate1 ) )

        if mate2:
            out.write( mate1 )
            out.write( mate2 )
        else:
            skip_count += 1

    if i is None:
        print "Your input file contained no valid FASTQ sequences."
    else:
        not_used_msg = mate_input.has_data()
        if not_used_msg:
            print not_used_msg
        print 'Interlaced %s pairs of sequences.' % ( i - skip_count + 1 )

    mate_input.close()
    out.close()

 
if __name__ == "__main__":
    main()
