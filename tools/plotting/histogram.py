#!/usr/bin/env python2.4
#Greg Von Kuster

import sys
from rpy import *

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def main():

    # Handle input params
    in_fname = sys.argv[1]
    out_fname = sys.argv[2] 
    try:
        column = int( sys.argv[3] ) - 1
    except:
        stop_err( "..Column not specified, your query does not contain a column of numerical data." )
    title = sys.argv[4]
    xlab = sys.argv[5]
    breaks = int( sys.argv[6] )
    if breaks == 0: breaks = "Sturges"
    if sys.argv[7] == "true": density = True
    else: density = False

    matrix = []
    skipped_lines = 0
    first_invalid_line = 0
    invalid_value = ''

    for i, line in enumerate( file( in_fname ) ):
        valid = True
        line = line.rstrip('\r\n')
        # Skip comments
        if line and not line.startswith( '#' ): 
            # Extract values and convert to floats
            row = []
            fields = line.split( "\t" )
            val = fields[column]
            if val.lower() == "na":
                row.append( float( "nan" ) )
            else:
                try:
                    row.append( float( val ) )
                except ValueError:
                    valid = False
                    skipped_lines += 1
                    if not first_invalid_line:
                        first_invalid_line = i+1
                        invalid_value = fields[column]
        else:
            valid = False
            skipped_lines += 1
            if not first_invalid_line:
                first_invalid_line = i+1

        if valid:
            matrix.append( row )

    if skipped_lines < i:
        print "..on columnn %s" %sys.argv[3]
        try:
            a = array( matrix )
            r.pdf( out_fname, 8, 8 )
            r.hist( a, probability=True, main=title, xlab=xlab, breaks=breaks )
            if density:
                r.lines( r.density( a ) )
            r.dev_off()
        except exc:
            stop_err("Building histogram resulted in error: %s." %str( exc ))
    else:
        print "..all values in column %s are non-numeric." %sys.argv[3]

    if skipped_lines > 0:
        print "..skipped %d invalid lines starting with line #%d.  Value '%s' is not numeric." % ( skipped_lines, first_invalid_line, invalid_value )

    r.quit( save="no" )
    
if __name__ == "__main__":
    main()
