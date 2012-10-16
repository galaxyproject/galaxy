#!/usr/bin/env python
"""
Build a UCSC genome browser custom track file
"""

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

FILE_TYPE_TO_TRACK_TYPE = { 'bed': None, 'bedstrict': None, 'bed6': None, 'bed12': None, 'bedgraph':'bedGraph', 'wig':'wiggle_0' }
CHUNK_SIZE = 2**20 #1mb

def get_track_line_is_interval( file_type, name, description, color, visibility  ):
    if file_type in FILE_TYPE_TO_TRACK_TYPE:
        track_type = FILE_TYPE_TO_TRACK_TYPE[ file_type ]
        is_interval = False
    else:
        track_type = None
        is_interval = True
    track_line = 'track '
    if track_type:
        track_line += 'type=%s ' % ( track_type )
    track_line += 'name="%s" description="%s" color=%s visibility=%s\n' % ( name, description, color, visibility )
    return track_line, is_interval

args = sys.argv[1:]

out_fname = args.pop(0)
out = open( out_fname, "w" )

num_tracks = 0
skipped_lines = 0
first_invalid_line = 0
while args:
    # Suck in one dataset worth of arguments
    in_fname = args.pop(0)
    file_type = args.pop(0)
    colspec = args.pop(0)
    name = args.pop(0)
    description = args.pop(0)
    color = args.pop(0).replace( '-', ',' )
    visibility = args.pop(0)
    track_line, is_interval = get_track_line_is_interval( file_type, name, description, color, visibility  )
    # Do the work
    in_file = open( in_fname )
    out.write( track_line )
    if not is_interval:
        while True:
            chunk = in_file.read( CHUNK_SIZE )
            if chunk:
                out.write( chunk )
            else:
                break
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
        
        i = 0
        for i, line in enumerate( in_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( "\t" )
                if st > 0:
                    #strand column is present
                    try:
                        out.write( "%s\t%s\t%s\t%d\t0\t%s\n" % ( fields[c], fields[s], fields[e], i, fields[st] ) )
                    except:
                        skipped_lines += 1
                        if not first_invalid_line:
                            first_invalid_line = i+1
                else:
                    try:
                       out.write( "%s\t%s\t%s\n" % ( fields[c], fields[s], fields[e] ) )
                    except:
                        skipped_lines += 1
                        if not first_invalid_line:
                            first_invalid_line = i+1
    out.write( "\n" ) #separating newline
    num_tracks += 1
    
out.close()

print "Generated a custom track containing %d subtracks." % num_tracks
if skipped_lines:
    print "Skipped %d invalid lines starting at #%d" % ( skipped_lines, first_invalid_line )



