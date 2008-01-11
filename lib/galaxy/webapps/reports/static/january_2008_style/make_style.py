#!/usr/bin/env python2.4

import pkg_resources; 
pkg_resources.require( "Cheetah" )

import sys
from Cheetah.Template import Template
import string
from subprocess import Popen, PIPE
import os.path

def run( cmd ):
    return Popen( cmd, stdout=PIPE).communicate()[0]

templates = [ ( "masthead.css.tmpl", "masthead.css"),
              ( "base.css.tmpl", "base.css" ) ]
            
images = [ 
           ( "./gradient.py 9 1000 $base_bg_top - $base_bg_bottom 0 0 $base_bg_bottom 1 1", "base_bg.png" ),
           ( "./gradient.py 9 50 $masthead_bg $masthead_bg_hatch", "masthead_bg.png" ),
           ( "./gradient.py 9 30 $footer_title_bg $footer_title_hatch 000000 0 0.5 000000 1 1", "footer_title_bg.png" )
           ]

vars, out_dir = sys.argv[1:]

context = dict()
for line in open( vars ):
    line = line.rstrip( '\r\n' )
    if line and not line.startswith( '#' ):
        key, value = line.split( '=' )
        if value.startswith( '"' ) and value.endswith( '"' ):
            value = value[1:-1]
        context[key] = value

for input, output in templates:
    print input ,"->", output
    open( os.path.join( out_dir, output ), "w" ).write( str( Template( file=input, searchList=[context] ) ) )

for rule, output in images:
    t = string.Template( rule ).substitute( context ) 
    print t, "->", output
    open( os.path.join( out_dir, output ), "w" ).write( run( t.split() ) )

