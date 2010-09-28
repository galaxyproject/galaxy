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
        columns = [options.column]
        styles = [('','n')[options.style == 'num']]
        orders = [('','r')[options.order == 'DESC']]
        col_style_orders = sys.argv[6:]
        if len(col_style_orders) > 1:
            columns.extend([col_style_orders[i] for i in range(0,len(col_style_orders),3)])
            styles.extend([('','n')[col_style_orders[i] == 'num'] for i in range(1,len(col_style_orders),3)])
            orders.extend([('','r')[col_style_orders[i] == 'DESC'] for i in range(2,len(col_style_orders),3)])
        cols = [ '-k%s,%s%s%s'%(columns[i], columns[i], styles[i], orders[i]) for i in range(len(columns)) ]
    except Exception, ex:
        stop_err('Error parsing input parameters\n' + str(ex))

    # Launch sort.
    cmd = "sort -f -t '	' %s %s %s" % (' '.join(cols), outputfile, inputfile)
    try:
        os.system(cmd)
    except Exception, ex:
        stop_err('Error running sort command\n' + str(ex))

if __name__ == "__main__":
    main()
