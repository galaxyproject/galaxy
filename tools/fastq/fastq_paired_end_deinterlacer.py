#Florent Angly
import sys
from galaxy_utils.sequence.fastq import fastqReader, fastqWriter, fastqNamedReader, fastqJoiner

def main():
    input_filename = sys.argv[1]
    input_type     = sys.argv[2] or 'sanger'
    mate1_filename = sys.argv[3]
    mate2_filename = sys.argv[4]

    type   = input_type
    input  = fastqNamedReader( open( input_filename, 'rb' ), format = type  )
    out1   = fastqWriter( open( mate1_filename, 'wb' ), format = type )
    out2   = fastqWriter( open( mate2_filename, 'wb' ), format = type )
    joiner = fastqJoiner( type )

    i = None
    skip_count = 0
    found = {}
    for i, mate1 in enumerate( fastqReader( open( input_filename, 'rb' ), format = type ) ):
     
        if mate1.identifier in found:
            del found[mate1.identifier]
            continue

        mate2 = input.get( joiner.get_paired_identifier( mate1 ) )

        if mate2:
            found[mate2.identifier] = None
            if joiner.is_first_mate( mate1 ):
                out1.write( mate1 )
                out2.write( mate2 )
            else:
                out1.write( mate2 )
                out2.write( mate1 )
        else:
            skip_count += 1

    if i is None:
        print "Your input file contained no valid FASTQ sequences."
    else:
        if skip_count:
            print '%i reads had no mate.' % skip_count
        print 'De-interlaced %s pairs of sequences.' % ( (i - skip_count + 1)/2 )

    input.close()
    out1.close()
    out2.close()
    
 
if __name__ == "__main__":
    main()
