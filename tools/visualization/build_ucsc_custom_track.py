#!/usr/bin/env python2.4
"""
Build a UCSC genome browser custom track file
"""

import sys, os

args = sys.argv[1:]

out_fname = args.pop(0)
out = open( out_fname, "w" )

num_tracks = 0

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
        for line in open( in_fname ):
            print >> out, line,
        print >> out
    elif type == "bed":
        print >> out, '''track name="%s" description="%s" color=%s visibility=%s''' \
                      % ( name, description, color, visibility )
        for line in open( in_fname ):
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
                print "Columns in interval file invalid for UCSC custom track."
                sys.exit()
        
        print >> out, '''track name="%s" description="%s" color=%s visibility=%s''' \
                      % ( name, description, color, visibility )
        i = 0
        for line in open( in_fname ):
            if line.startswith( "#" ):
                continue
            fields = line.split( "\t" )
            if st > 0 and st < len( fields ):
                print >> out, "%s\t%s\t%s\t%d\t0\t%s" % ( fields[c], fields[s], fields[e], i, fields[st] )
            else:
                print >> out, "%s\t%s\t%s" % ( fields[c], fields[s], fields[e] )
            i += 1
        print >> out
    num_tracks += 1
    
out.close()

print "Generated a custom track containing %d subtracks." % num_tracks



