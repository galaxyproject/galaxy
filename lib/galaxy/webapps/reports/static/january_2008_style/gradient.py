#!/usr/bin/env python

"""
usage: %prog width height bg_color hatch_color [color alpha stop_pos] +
"""

from __future__ import division

import sys
import cairo

assert sys.version_info[:2] >= ( 2, 4 )

def parse_css_color( color ):
    if color.startswith( '#' ):
        color = color[1:]
    if len( color ) == 3:
        r = int( color[0], 16 )
        g = int( color[1], 16 )
        b = int( color[2], 16 )
    elif len( color ) == 6:
        r = int( color[0:2], 16 )
        g = int( color[2:4], 16 )
        b = int( color[4:6], 16 )
    else:
        raise Exception( "Color should be 3 hex numbers" )
    return r/256, g/256, b/256
        
def gradient( width, height, args ):
    pat = cairo.LinearGradient(0.0, 0.0, 0.0, height)
    while len( args ) > 2:
        col = parse_css_color( args[0] )
        alpha = float( args[1])
        pos = float( args[2] )
        pat.add_color_stop_rgba( pos, col[0], col[1], col[2], alpha )
        args = args[3:]
    return pat
    
def hatch( width, height, color ):
    im_surf = cairo.ImageSurface( cairo.FORMAT_ARGB32, width, width )
    c = cairo.Context( im_surf )
    c.set_source_rgb ( *color )
    c.set_line_width( 0.75 )
    for i in range( 0, 2*max(height,width), 3 ):
        c.move_to ( 0-10, i+10 )
        c.line_to ( width+10, i - width - 10 )
    c.stroke()
    pat = cairo.SurfacePattern( im_surf )
    pat.set_extend (cairo.EXTEND_REPEAT)
    return pat
                
width = int( sys.argv[1] )
height = int( sys.argv[2] )
    
surface = cairo.ImageSurface( cairo.FORMAT_ARGB32, width, height )
c = cairo.Context( surface )

c.rectangle(0,0,width,height)
c.set_source_rgb( *parse_css_color( sys.argv[3] ) )
c.fill()

if sys.argv[4] != "-":
    c.rectangle (0, 0, width, height)
    c.set_source( hatch( width, height, parse_css_color( sys.argv[4] ) ) )
    c.fill()

pat = cairo.LinearGradient(0.0, 0.0, 0.0, height)
pat.add_color_stop_rgba( 0, 1, 1, 1, 0 )
pat.add_color_stop_rgba( 1, 1, 1, 1, 1 )
c.rectangle (0, 0, width, height)
c.set_source( gradient( width, height, sys.argv[5:] ) )
c.fill()

surface.write_to_png( "/dev/stdout" )
