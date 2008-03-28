#!/usr/bin/env python

import sys
from Cheetah.Template import Template
import string
from subprocess import Popen, PIPE
import os.path

assert sys.version_info[:2] >= ( 2, 4 )

def run( cmd ):
    return Popen( cmd, stdout=PIPE).communicate()[0]

templates = [ ( "base.css.tmpl", "base.css" ),
              ( "masthead.css.tmpl", "masthead.css"),
              ( "history.css.tmpl", "history.css" ),
              ( "tool_menu.css.tmpl", "tool_menu.css" ) ]
              
images = [ ( "./gradient.py 9 1000 $menu_bg_top $menu_bg_hatch FFFFFF 0 0 FFFFFF 1 1", "menu_bg.png" ),
           ( "./gradient.py 9 1000 $base_bg_top - FFFFFF 0 0 FFFFFF 1 1", "base_bg.png" ),
           ( "./gradient.py 9 50 $masthead_bg $masthead_bg_hatch 000000 0 0.5 000000 1 1", "masthead_bg.png" ),
           ( "./gradient.py 9 30 $footer_title_bg $footer_title_hatch 000000 0 0.5 000000 1 1", "footer_title_bg.png" ),
           ( "./gradient.py 9 50 $form_title_bg $form_title_bg_hatch FFFFFF 0 0 FFFFFF 0.5 1", "form_title_bg.png" ),
           ( "./gradient.py 9 200 $history_ok_bg - FFFFFF 0 0.5 FFFFFF 0.5 1", "ok_bg.png" ),
           ( "./gradient.py 9 200 $history_error_bg - FFFFFF 0 0.5 FFFFFF 0.5 1", "error_bg.png" ),
           ( "./gradient.py 9 200 $history_running_bg - FFFFFF 0 0.5 FFFFFF 0.5 1", "warn_bg.png" ),
           ( "./gradient.py 9 200 $history_queued_bg - FFFFFF 0 0.5 FFFFFF 0.5 1", "gray_bg.png" ) ]

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
    open( os.path.join( out_dir, output ), "w" ).write( str( Template( file=input, searchList=[context] ) ) )
    
for rule, output in images:
    t = string.Template( rule ).substitute( context ) 
    print t, "->", output
    open( os.path.join( out_dir, output ), "w" ).write( run( t.split() ) )
    
for src, bg, out in shared_images:
    t = "./png_over_color.py shared_images/%s %s %s" % ( src, context[bg], os.path.join( out_dir, out ) )
    print t
    run( t.split() )