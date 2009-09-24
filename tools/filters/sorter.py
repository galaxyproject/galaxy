"""
Sorts tabular data on one or more columns.

usage: %prog [options]
   -i, --input=i: Tabular file to be sorted
   -o, --out_file1=o: Sorted output file
   -c, --column=c: First column to sort on
   -s, --style=s: Sort style (numerical or alphabetical)
   -r, --order=r: Order (ASC or DESC)

usage: %prog input out_file1 column style order [column style ...]
"""

import os, re, string, sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def main():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    try:
        inputfile = options.input
        outputfile = '-o %s' % options.out_file1
        order = ('', '-r')[options.order == 'DESC']
        columns = [options.column]
        styles = [('','n')[options.style == 'num']]
        col_styles = sys.argv[6:]
        if len(col_styles) > 1:
            columns.extend([col_styles[i] for i in range(0,len(col_styles),2)])
            styles.extend([('','n')[col_styles[i] == 'num'] for i in range(1,len(col_styles),2)])
        cols = [ '-k%s,%s%s'%(columns[i], columns[i], styles[i]) for i in range(len(columns)) ]
    except Exception, ex:
        stop_err('Error parsing input parameters\n' + str(ex))

    # Launch sort.
    cmd = "sort -f -t $'\t' %s %s %s %s" % (order, ' '.join(cols), outputfile, inputfile)
    try:
        os.system(cmd)
    except Exception, ex:
        stop_err('Error running sort command\n' + str(ex))

if __name__ == "__main__":
    main()
