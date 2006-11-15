#!/usr/bin/env python

"""
Calculate covariance / correlations between numeric columns in a tab delim file.

usage: %prog infile output.txt cov_or_cor method columns
"""

import sys
from Numeric import *
from rpy import *

def fail( message ):
    print >> sys.stderr, message
    return -1

def main():

    method = sys.argv[3]
    assert method in ( "pearson", "kendall", "spearman" )

    columns = map( int, sys.argv[4].split( ',' ) )
    
    matrix = []

    for i, line in enumerate( open( sys.argv[1] ) ):
        # Skip comments
        if line.startswith( '#' ): 
            continue
        # Extract values and convert to floats
        row = []
        for column in columns:
            column -= 1
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

    # Run correlation
    
    value = r.cor( array( matrix ), use="pairwise.complete.obs", method=method )
    
    out = open( sys.argv[2], "w" )
    for row in value:
        print >> out, "\t".join( map( str, row ) )
    out.close()

if __name__ == "__main__":
    main()
