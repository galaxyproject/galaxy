#!/usr/bin/env python
#Greg Von Kuster

import sys
from rpy import *

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def main():

    in_fname = sys.argv[1]
    out_fname = sys.argv[2]
    try:
        columns = int( sys.argv[3] ) - 1, int( sys.argv[4] ) - 1
    except:
        stop_err( "Columns not specified, your query does not contain a column of numerical data." )
    title = sys.argv[5]
    xlab = sys.argv[6]
    ylab = sys.argv[7]
    out_type = sys.argv[8]
    out_width = int(sys.argv[9])
    out_height = int(sys.argv[10])
    point_size = float(sys.argv[11])


    xvec=[]
    yvec=[]
    skipped_lines = 0
    first_invalid_line = 0
    invalid_value = ''
    invalid_column = 0
    i = 0
    for i, line in enumerate( file( in_fname ) ):
        valid = True
        vals = []
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ): 
            row = []
            fields = line.split( "\t" )
            for c,column in enumerate(columns):
                try:
                    val = fields[column]
                    if val.lower() == "na": 
                        v = float( "nan" ) 
                    else:
                        v = float( fields[column] )
                    vals.append(val) 
                except:
                    valid = False
                    skipped_lines += 1
                    if not first_invalid_line:
                        first_invalid_line = i + 1
                        try:
                            invalid_value = fields[column]
                        except:
                            invalid_value = ''
                        invalid_column = column + 1
                    break
        else:
            valid = False
            skipped_lines += 1
            if not first_invalid_line:
                first_invalid_line = i+1

        if valid:
            xvec.append(vals[0])
            yvec.append(vals[1])
    if skipped_lines < i:
        try:
            if out_type == "jpg":
                r.jpeg(out_fname,width=out_width,height=out_height)
            elif out_type == "png":
                # type="cairo" needed to be set for headless servers
                r.png(out_fname,type="cairo",width=out_width,height=out_height)
            else:
                r.pdf(out_fname, out_width, out_height)

            r.plot(xvec,yvec, type="p", main=title, xlab=xlab, ylab=ylab, col="blue", pch=19,cex=point_size )
            r.dev_off()
        except Exception, exc:
            stop_err( "%s" %str( exc ) )
    else:
        stop_err( "All values in both columns %s and %s are non-numeric or empty." % ( sys.argv[3], sys.argv[4] ) )

    print "Scatter plot on columns %s, %s. " % ( sys.argv[3], sys.argv[4] )
    if skipped_lines > 0:
        print "Skipped %d lines starting with line #%d, value '%s' in column %d is not numeric." % ( skipped_lines, first_invalid_line, invalid_value, invalid_column )

    r.quit( save="no" )

if __name__ == "__main__":
    main()
