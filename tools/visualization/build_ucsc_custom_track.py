#!/usr/bin/env python
"""
Build a UCSC genome browser custom track file
"""

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

args = sys.argv[1:]

out_fname = args.pop(0)
out = open( out_fname, "w" )

num_tracks = 0
skipped_lines = 0
first_invalid_line = 0
while args:
    # Suck in one dataset worth of arguments
    in_fname = args.pop(0)
    type = args.pop(0)
    colspec = args.pop(0)
    name = args.pop(0)
    description = args.pop(0)
    color = args.pop(0).replace( '-', ',' )
    visibility = args.pop(0)
    # Do the work
    if type == "wig":
        print >> out, '''track type=wiggle_0 name="%s" description="%s" color=%s visibility=%s''' \
                      % ( name, description, color, visibility )
        for i, line in enumerate( file( in_fname ) ):
            print >> out, line,
        print >> out
    elif type == "bed":
        print >> out, '''track name="%s" description="%s" color=%s visibility=%s''' \
                      % ( name, description, color, visibility )
        for i, line in enumerate( file( in_fname ) ):
            print >> out, line,
        print >> out
    else:
        # Assume type is interval (don't pass this script anything else!)
        try:
            c, s, e, st = [ int( x ) - 1 for x in colspec.split( "," ) ]
        except:
            try:
                c, s, e = [ int( x ) - 1 for x in colspec.split( "," )[:3] ]
                st = -1    #strand column is absent
            except:
                stop_err( "Columns in interval file invalid for UCSC custom track." )
        
        print >> out, '''track name="%s" description="%s" color=%s visibility=%s''' \
                      % ( name, description, color, visibility )
        i = 0
        for i, line in enumerate( file( in_fname ) ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( "\t" )
                if st > 0:
                    #strand column is present
                    try:
                        print >> out, "%s\t%s\t%s\t%d\t0\t%s" % ( fields[c], fields[s], fields[e], i, fields[st] )
                    except:
                        skipped_lines += 1
                        if not first_invalid_line:
                            first_invalid_line = i+1
                else:
                    try:
                        print >> out, "%s\t%s\t%s" % ( fields[c], fields[s], fields[e] )
                    except:
                        skipped_lines += 1
                        if not first_invalid_line:
                            first_invalid_line = i+1
        print >> out
    num_tracks += 1
    
out.close()

print "Generated a custom track containing %d subtracks." % num_tracks
if skipped_lines:
    print "Skipped %d invalid lines starting at #%d" % ( skipped_lines, first_invalid_line )



