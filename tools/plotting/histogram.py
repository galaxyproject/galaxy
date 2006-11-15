#!/usr/bin/env python2.4

import sys, rpy
from Numeric import *
from rpy import *

def fail( message ):
    print >> sys.stderr, message
    return -1

def main():

    in_fname = sys.argv[1]
    out_fname = sys.argv[2]
    
    columns = ( int( sys.argv[3] ) - 1 ),
    
    title = sys.argv[4]
    xlab = sys.argv[5]
    
    breaks = int( sys.argv[6] )
    if breaks == 0: breaks = "Sturges"
    
    if sys.argv[7] == "true": density = True
    else: density = False

    matrix = []
    nan_row = False
    for i, line in enumerate( open( sys.argv[1] ) ):
        # Skip comments
        if  line.startswith( '#' ) or ( sys.argv[8] == "true" and i == 0 ): 
            continue
        # Extract values and convert to floats
        row = []
        for column in columns:
            fields = line.split( "\t" )
            if len( fields ) <= column:
                return fail( "No column %d on line %d" % ( column+1, i ) )
            val = fields[column]
            if val.lower() == "na": 
                nan_row = True
            else:
                try:
                    row.append( float( fields[column] ) )
                except ValueError:
                    return fail( "Value '%s' in column %d on line %d is not numeric" % ( fields[column], column+1, i ) )
        if not nan_row:
            matrix.append( row )
        
    a = array( matrix )
        
    r.pdf( out_fname, 8, 8 )
    r.hist( a, probability=True, main=title, xlab=xlab, breaks=breaks )
    if density:
        r.lines( r.density( a ) )
    r.dev_off()
    r.quit( save="no" )
    
if __name__ == "__main__":
    main()
