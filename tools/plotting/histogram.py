#!/usr/bin/env python
#Greg Von Kuster

import sys
from rpy import *

assert sys.version_info[:2] >= ( 2, 4 )

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
        stop_err( "Column not specified, your query does not contain a column of numerical data." )
    title = sys.argv[4]
    xlab = sys.argv[5]
    breaks = int( sys.argv[6] )
    if breaks == 0:
        breaks = "Sturges"
    if sys.argv[7] == "true":
        density = True
    else: density = False
    if len( sys.argv ) >= 9 and sys.argv[8] == "true":
        frequency = True
    else: frequency = False

    matrix = []
    skipped_lines = 0
    first_invalid_line = 0
    invalid_value = ''
    i = 0
    for i, line in enumerate( file( in_fname ) ):
        valid = True
        line = line.rstrip('\r\n')
        # Skip comments
        if line and not line.startswith( '#' ): 
            # Extract values and convert to floats
            row = []
            try:
                fields = line.split( "\t" )
                val = fields[column]
                if val.lower() == "na":
                    row.append( float( "nan" ) )
            except:
                valid = False
                skipped_lines += 1
                if not first_invalid_line:
                    first_invalid_line = i+1
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
            matrix += row

    if skipped_lines < i:
        try:
            a = r.array( matrix )
            r.pdf( out_fname, 8, 8 )
            histogram = r.hist( a, probability=not frequency, main=title, xlab=xlab, breaks=breaks )
            if density:
                density = r.density( a )
                if frequency:
                    scale_factor = len( matrix ) * ( histogram['mids'][1] - histogram['mids'][0] ) #uniform bandwidth taken from first 2 midpoints
                    density[ 'y' ] = map( lambda x: x * scale_factor, density[ 'y' ] )
                r.lines( density )
            r.dev_off()
        except Exception, exc:
            stop_err( "%s" %str( exc ) )
    else:
        if i == 0:
            stop_err("Input dataset is empty.")
        else:
            stop_err( "All values in column %s are non-numeric." %sys.argv[3] )

    print "Histogram of column %s. " %sys.argv[3]
    if skipped_lines > 0:
        print "Skipped %d invalid lines starting with line #%d, '%s'." % ( skipped_lines, first_invalid_line, invalid_value )

    r.quit( save="no" )
    
if __name__ == "__main__":
    main()
