#!/usr/bin/env python

#from galaxy import eggs
#import pkg_resources
#pkg_resources.require("Cheetah")

import sys, string, os.path, tempfile, subprocess
#from galaxy import eggs
import pkg_resources
pkg_resources.require( "Cheetah" )

from Cheetah.Template import Template
from subprocess import Popen, PIPE

assert sys.version_info[:2] >= ( 2, 4 )

# To create a new style ( this is an example ):
# python make_style.py blue_colors.ini blue

def run( cmd ):
    return Popen( cmd, stdout=PIPE).communicate()[0]

templates = [ ( "base.css.tmpl", "base.css" ),
              ( "panel_layout.css.tmpl", "panel_layout.css" ),
              ( "masthead.css.tmpl", "masthead.css"),
              ( "library.css.tmpl", "library.css"),
              ( "history.css.tmpl", "history.css" ),
              ( "tool_menu.css.tmpl", "tool_menu.css" ),
              ( "iphone.css.tmpl", "iphone.css" ),
              ( "reset.css.tmpl", "reset.css" ) ]
              
images = [ 
           ( "./gradient.py 9 30 $panel_header_bg_top - $panel_header_bg_bottom 0 0 $panel_header_bg_bottom 1 1", "panel_header_bg.png" ),
           ( "./gradient.py 9 30 $panel_header_bg_bottom - $panel_header_bg_top 0 0 $panel_header_bg_top 1 1", "panel_header_bg_pressed.png" ),
           ( "./gradient.py 9 1000 $menu_bg_top $menu_bg_hatch $menu_bg_over 0 0 $menu_bg_over 1 1", "menu_bg.png" ),
           ( "./gradient.py 9 1000 $base_bg_top - $base_bg_bottom 0 0 $base_bg_bottom 1 1", "base_bg.png" ),
           ( "./gradient.py 9 500 $form_body_bg_top - $form_body_bg_bottom 0 0 $form_body_bg_bottom 1 1", "form_body_bg.png" ),
           ( "./gradient.py 9 50 $masthead_bg $masthead_bg_hatch", "masthead_bg.png" ),
           ( "./gradient.py 9 30 $footer_title_bg $footer_title_hatch 000000 0 0.5 000000 1 1", "footer_title_bg.png" ),
           ( "./gradient.py 9 50 $form_title_bg_top $form_title_bg_hatch $form_title_bg_bottom 0 0 $form_title_bg_bottom 1 1", "form_title_bg.png" ),
           ( "./gradient.py 9 200 $history_ok_bg - FFFFFF 0 0.5 FFFFFF 0.5 1", "ok_bg.png" ),
           ( "./gradient.py 9 200 $history_error_bg - FFFFFF 0 0.5 FFFFFF 0.5 1", "error_bg.png" ),
           ( "./gradient.py 9 200 $history_running_bg - FFFFFF 0 0.5 FFFFFF 0.5 1", "warn_bg.png" ),
           ( "./gradient.py 9 200 $history_queued_bg - FFFFFF 0 0.5 FFFFFF 0.5 1", "gray_bg.png" ),
           ( "./callout_top.py 20 10 $panel_header_bg_top $layout_border", "popupmenu_callout_top.png" ),
           ( "./circle.py 12 #FFFFFF #D8B365 right > workflow_circle_open.png" ),
           ( "./circle.py 12 #BBFFBB #D8B365 right > workflow_circle_green.png" ),
           ( "./circle.py 12 #FFFFFF #D8B365 none> workflow_circle_drag.png" ),
           ]

shared_images = [ 
    # Dialog boxes
    ( "ok_large.png", "done_message_bg", "done_message_icon.png" ),
    ( "info_large.png", "info_message_bg", "info_message_icon.png" ),
    ( "warn_large.png", "warn_message_bg", "warn_message_icon.png" ),
    ( "error_large.png", "error_message_bg", "error_message_icon.png" ),
    # History icons
    ( "ok_small.png", "history_ok_bg", "data_ok.png" ),
    ( "error_small.png", "history_error_bg", "data_error.png" ),
    ( "wait_small.png", "history_queued_bg", "data_queued.png" ) ]


vars, out_dir = sys.argv[1:]

context = dict()
for line in open( vars ):
    if line.startswith( '#' ):
        continue
    key, value = line.rstrip("\r\n").split( '=' )
    if value.startswith( '"' ) and value.endswith( '"' ):
        value = value[1:-1]
    context[key] = value

for input, output in templates:
    print input ,"->", output
    out_fname = os.path.join( out_dir, output )
    temp_file = tempfile.NamedTemporaryFile()
    # Write processed template to temporary file
    print "Processing template..."
    temp_file.write( str( Template( file=input, searchList=[context] ) ) )
    temp_file.flush()
    # Compress CSS with YUI
    print "Compressing..."
    subprocess.call( 
        "java -jar ../../scripts/yuicompressor.jar --type css %s -o %s" % ( temp_file.name, out_fname ),
        shell = True )

  
"""
for rule, output in images:
    t = string.Template( rule ).substitute( context ) 
    print t, "->", output
    open( os.path.join( out_dir, output ), "w" ).write( run( t.split() ) )
    
for src, bg, out in shared_images:
    t = "./png_over_color.py shared_images/%s %s %s" % ( src, context[bg], os.path.join( out_dir, out ) )
    print t
    run( t.split() )
"""
