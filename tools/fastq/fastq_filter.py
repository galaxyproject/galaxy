#Dan Blankenberg
import sys, os, shutil
from galaxy_utils.sequence.fastq import fastqReader, fastqWriter

def main():
    #Read command line arguments
    input_filename = sys.argv[1]
    script_filename = sys.argv[2]
    output_filename = sys.argv[3]
    additional_files_path = sys.argv[4]
    input_type = sys.argv[5] or 'sanger'
    
    #Save script file for debuging/verification info later
    os.mkdir( additional_files_path )
    shutil.copy( script_filename, os.path.join( additional_files_path, 'debug.txt' ) )
    
    out = fastqWriter( open( output_filename, 'wb' ), format = input_type )
    
    i = None
    reads_kept = 0
    for i, fastq_read in enumerate( fastqReader( open( input_filename ), format = input_type ) ):
        local = {'fastq_read':fastq_read, 'ret_val':False}
        execfile( script_filename, {}, local )
        if local['ret_val']:
            out.write( fastq_read )
            reads_kept += 1
    out.close()
    if i is None:
        print "Your file contains no valid fastq reads."
    else:
        print 'Kept %s of %s reads (%.2f%%).' % ( reads_kept, i + 1, float( reads_kept ) / float( i + 1 ) * 100.0 )

if __name__ == "__main__":
    main()
