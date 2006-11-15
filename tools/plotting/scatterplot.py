#!/usr/bin/env python

import sys
from Numeric import *
from rpy import *

def fail( message ):
    print >> sys.stderr, message
    return -1

def main():

    in_fname = sys.argv[1]
    out_fname = sys.argv[2]
    
    columns = int( sys.argv[3] ) - 1, int( sys.argv[4] ) - 1
    
    title = sys.argv[5]
    xlab = sys.argv[6]
    ylab = sys.argv[7]

    matrix = []
    for i, line in enumerate( open( sys.argv[1] ) ):
        # Skip comments
        if line.startswith( '#' ): 
            continue
        # Extract values and convert to floats
        row = []
        for column in columns:
            fields = line.split( "\t" )
            if len( fields ) <= column:
                return fail( "No column %d on line %d" % ( column+1, i ) )
            val = fields[column]
            if val.lower() == "na": 
                row.append( float( "nan" ) )
            else:
                try:
                    row.append( float( fields[column] ) )
                except ValueError:
                    return fail( "Value '%s' in column %d on line %d is not numeric" % ( fields[column], column+1, i ) )
        matrix.append( row )
        
    r.pdf( out_fname, 8, 8 )
    r.plot( array( matrix ), type="p", main=title, xlab=xlab, ylab=ylab, col="blue", pch=19 )
    r.dev_off()
    r.quit( save="no" )
    
if __name__ == "__main__":
    main()
