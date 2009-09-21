# This script sorts a file based on the inputs: 
# -cols		- column to sort on
# -order	- ASC- or DESCending order
# -i		- input filename 
# -o		- output filename

import os, re, string, sys

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def main():
    try:
        inputfile = sys.argv[1]
        outputfile = '-o %s' % sys.argv[2]
        order = ('', '-r')[sys.argv[3] == 'DESC']
        sort_type = ('','-n')[sys.argv[4] == 'num']
        columns = sys.argv[5:]
        cols = [ '-k%s,%s'%(n, n) for n in columns ]
    except Exception, ex:
        stop_err('Error parsing input parameters\n' + str(ex))

    # Launch sort.
    cmd = "sort -f -t $'\t' %s %s %s %s %s" % (sort_type, ' '.join(cols), order, outputfile, inputfile)
    try:
        os.system(cmd)
    except Exception, ex:
        stop_err('Error running sort command\n' + str(ex))

if __name__ == "__main__":
    main()
