#!/usr/bin/env python

import sys
from Numeric import *
from rpy import *

def fail( message ):
    print >> sys.stderr, message
    sys.exit()

def main():

    in_fname = sys.argv[1]
    out_fname = sys.argv[2]
    
    columns = int( sys.argv[3] ) - 1, int( sys.argv[4] ) - 1
    
    title = sys.argv[5]
    xlab = sys.argv[6]
    ylab = sys.argv[7]

    matrix = []
    skipped_lines = 0
    first_invalid_line = 0
    invalid_value = ''
    invalid_column = 0

    for i, line in enumerate( file ( sys.argv[1] ) ):
        valid = True
        line = line.rstrip('\r\n')
        if line and not line.startswith( '#' ): 
            # Extract values and convert to floats
            row = []
            for column in columns:
                if not valid:
                    break
                fields = line.split( "\t" )
                if len( fields ) <= column:
                    return fail( "Column %d on line %d missing, line: %s" % ( column+1, i, line ) )
                val = fields[column]
                if val.lower() == "na": 
                    row.append( float( "nan" ) )
                else:
                    try:
                        row.append( float( fields[column] ) )
                    except:
                        valid = False
                        skipped_lines += 1
                        if not first_invalid_line:
                            first_invalid_line = i+1
                            invalid_value = fields[column]
                            invalid_column = column+1
        else:
            valid = False
            skipped_lines += 1
            if not first_invalid_line:
                first_invalid_line = i+1

        if valid:
            matrix.append( row )
        
    r.pdf( out_fname, 8, 8 )
    r.plot( array( matrix ), type="p", main=title, xlab=xlab, ylab=ylab, col="blue", pch=19 )
    r.dev_off()

    msg = "--Scatter plot on "
    for i,col in enumerate(columns):
        col += 1
        msg += "c%d, " %col
    if skipped_lines > 0:
        msg += " skipped %d lines starting with line #%d.  Value '%s' in column %d is not numeric." % ( skipped_lines, first_invalid_line, invalid_value, invalid_column )

    print msg

    r.quit( save="no" )

if __name__ == "__main__":
    main()
