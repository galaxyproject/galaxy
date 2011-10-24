#Florent Angly
import sys
from galaxy_utils.sequence.fastq import fastqReader, fastqWriter, fastqNamedReader, fastqJoiner

def main():
    input_filename   = sys.argv[1]
    input_type       = sys.argv[2] or 'sanger'
    mate1_filename   = sys.argv[3]
    mate2_filename   = sys.argv[4]
    single1_filename = sys.argv[5]
    single2_filename = sys.argv[6]

    type        = input_type
    input       = fastqNamedReader( open( input_filename, 'rb' ), format = type  )
    mate1_out   = fastqWriter( open( mate1_filename, 'wb' ), format = type )
    mate2_out   = fastqWriter( open( mate2_filename, 'wb' ), format = type )
    single1_out = fastqWriter( open( single1_filename, 'wb' ), format = type )
    single2_out = fastqWriter( open( single2_filename, 'wb' ), format = type )
    joiner      = fastqJoiner( type )

    i = None
    skip_count = 0
    found = {}
    for i, read in enumerate( fastqReader( open( input_filename, 'rb' ), format = type ) ):
     
        if read.identifier in found:
            del found[read.identifier]
            continue

        mate1 = input.get( read.identifier )

        mate2 = input.get( joiner.get_paired_identifier( mate1 ) )

        if mate2:
            # This is a mate pair
            found[mate2.identifier] = None
            if joiner.is_first_mate( mate1 ):
                mate1_out.write( mate1 )
                mate2_out.write( mate2 )
            else:
                mate1_out.write( mate2 )
                mate2_out.write( mate1 )
        else:
            # This is a single
            skip_count += 1
            if joiner.is_first_mate( mate1 ):
                single1_out.write( mate1 )
            else:
                single2_out.write( mate1 )

    if i is None:
        print "Your input file contained no valid FASTQ sequences."
    else:
        if skip_count:
            print 'There were %i reads with no mate.' % skip_count
        print 'De-interlaced %s pairs of sequences.' % ( (i - skip_count + 1)/2 )

    input.close()
    mate1_out.close()
    mate2_out.close()
    single1_out.close()
    single2_out.close()

 
if __name__ == "__main__":
    main()
