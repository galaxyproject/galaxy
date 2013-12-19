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
    
    ## Dan, Others: Can we simply drop the "format=input_type" here since it is specified in reader.
    ## This optimization would cut runtime roughly in half (for my test case anyway). -John
    out = fastqWriter( open( output_filename, 'wb' ), format = input_type )
    
    i = None
    reads_kept = 0
    execfile(script_filename, globals())
    for i, fastq_read in enumerate( fastqReader( open( input_filename ), format = input_type ) ):
        ret_val = fastq_read_pass_filter( fastq_read )  ## fastq_read_pass_filter defined in script_filename
        if ret_val:
            out.write( fastq_read )
            reads_kept += 1
    out.close()
    if i is None:
        print "Your file contains no valid fastq reads."
    else:
        print 'Kept %s of %s reads (%.2f%%).' % ( reads_kept, i + 1, float( reads_kept ) / float( i + 1 ) * 100.0 )

if __name__ == "__main__":
    main()
