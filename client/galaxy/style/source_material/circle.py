#!/usr/bin/env python
"""
usage: %prog width height bg_color hatch_color [color alpha stop_pos] +
"""
from __future__ import division

import sys
from math import pi

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
    return r / 256, g / 256, b / 256


size = int( sys.argv[1] )

surface = cairo.ImageSurface( cairo.FORMAT_ARGB32, size, size )
c = cairo.Context( surface )

c.set_line_width( 1 )

c.arc( size / 2.0, size / 2.0, ( size - 1 ) / 2.0, 0, 2 * pi )

c.set_source_rgb( *parse_css_color( sys.argv[2] ) )
c.fill_preserve()

c.set_source_rgb( *parse_css_color( sys.argv[3] ) )
c.stroke()

t = size / 4.0

arrow = sys.argv[4]
if arrow == 'right':
    c.move_to( t + 1, t )
    c.line_to( 3 * t - 1, 2 * t )
    c.line_to( t + 1, 3 * t )
    c.stroke()

surface.write_to_png( "/dev/stdout" )
