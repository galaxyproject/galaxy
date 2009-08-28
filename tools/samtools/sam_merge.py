#! /usr/bin/python

import os, sys

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def __main__():
    infile =  sys.argv[1]
    outfile = sys.argv[2]
    if len( sys.argv ) < 3:
        stop_err( 'No files to merge' )
    filenames = sys.argv[3:]
    cmd1 = 'samtools merge %s %s %s' % (outfile, infile, ' '.join(filenames))
    try:
        os.system(cmd1)
    except Exception, eq:
        stop_err('Error running SAMtools merge tool\n' + str(eq))
            
if __name__ == "__main__" : __main__()