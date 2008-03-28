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
        r = int( color[0]*2, 16 )
        g = int( color[1]*2, 16 )
        b = int( color[2]*2, 16 )
    elif len( color ) == 6:
        r = int( color[0:2], 16 )
        g = int( color[2:4], 16 )
        b = int( color[4:6], 16 )
    else:
        raise Exception( "Color should be 3 hex numbers" )
    return r/256, g/256, b/256
                        
width = int( sys.argv[1] )
height = int( sys.argv[2] )
    
surface = cairo.ImageSurface( cairo.FORMAT_ARGB32, width, height )
c = cairo.Context( surface )

height -= 1
width -= 1

hw = width / 2

c.set_line_width( 1 )

def t( x ): return x + 0.5

c.move_to( t( 0 ), t( height+2 ) )
c.line_to( t( hw ), t( 0 ) )
c.line_to( t( width ), t( height+2 ) )
c.close_path()

c.set_source_rgb( *parse_css_color( sys.argv[3] ) )
c.fill_preserve()

c.set_source_rgb( *parse_css_color( sys.argv[4] ) )
c.stroke()

surface.write_to_png( "/dev/stdout" )
