#Florent Angly
import sys
from galaxy_utils.sequence.fastq import fastqReader, fastqWriter, fastqNamedReader, fastqJoiner

def main():
    mate1_filename   = sys.argv[1]
    mate1_type       = sys.argv[2] or 'sanger'
    mate2_filename   = sys.argv[3]
    mate2_type       = sys.argv[4] or 'sanger'
    outfile_pairs    = sys.argv[5]
    outfile_singles = sys.argv[6]

    if mate1_type != mate2_type:
        print "WARNING: You are trying to interlace files of two different types: %s and %s." % ( mate1_type, mate2_type )
        return

    type = mate1_type
    joiner = fastqJoiner( type )
    out_pairs = fastqWriter( open( outfile_pairs, 'wb' ), format = type )
    out_singles = fastqWriter( open( outfile_singles, 'wb' ), format = type )

    # Pairs + singles present in mate1
    nof_singles = 0
    nof_pairs   = 0
    mate2_input = fastqNamedReader( open( mate2_filename, 'rb' ), format = type )
    i = None
    for i, mate1 in enumerate( fastqReader( open( mate1_filename, 'rb' ), format = type ) ):
        mate2 = mate2_input.get( joiner.get_paired_identifier( mate1 ) )
        if mate2:
            out_pairs.write( mate1 )
            out_pairs.write( mate2 )
            nof_pairs += 1
        else:
            out_singles.write( mate1 )
            nof_singles += 1

    # Singles present in mate2
    mate1_input = fastqNamedReader( open( mate1_filename, 'rb' ), format = type )
    j = None
    for j, mate2 in enumerate( fastqReader( open( mate2_filename, 'rb' ), format = type ) ):
        mate1 = mate1_input.get( joiner.get_paired_identifier( mate2 ) )
        if not mate1:
            out_singles.write( mate2 )
            nof_singles += 1

    if (i is None) and (j is None):
        print "Your input files contained no valid FASTQ sequences."
    else:
        print 'There were %s single reads.' % ( nof_singles )
        print 'Interlaced %s pairs of sequences.' % ( nof_pairs )

    mate1_input.close()
    mate2_input.close()
    out_pairs.close()
    out_singles.close()

 
if __name__ == "__main__":
    main()
