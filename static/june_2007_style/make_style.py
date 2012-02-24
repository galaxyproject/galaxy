#!/usr/bin/env python

import sys, string, os, tempfile, subprocess

# from Cheetah.Template import Template
from subprocess import Popen, PIPE

assert sys.version_info[:2] >= ( 2, 4 )

# To create a new style ( this is an example ):
# In case you have not yet installed required packages:
# % sudo easy_install pyparsing 
# % sudo easy_install http://effbot.org/downloads/Imaging-1.1.7.tar.gz
# When you have the above installed, add whatever new style you want to /static/june_2007_style/blue_colors.ini and then:
# % cd ~/static/june_2007_style/
# % python make_style.py blue_colors.ini blue

def run( cmd ):
    return Popen( cmd, stdout=PIPE).communicate()[0]

# TODO: Are these images still being used?  If not, clean this code up!
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

# TODO: Are these shared_images still being used?  If not, clean this code up!
shared_images = [ 
    # Dialog boxes
    ( "ok_large.png", "done_message_bg", "done_message_icon.png" ),
    ( "info_large.png", "info_message_bg", "info_message_icon.png" ),
    ( "warn_large.png", "warn_message_bg", "warn_message_icon.png" ),
    ( "error_large.png", "error_message_bg", "error_message_icon.png" ),
    # History icons
    ( "ok_small.png", "history_ok_bg", "data_ok.png" ),
    ( "error_small.png", "history_error_bg", "data_error.png" ),
    ( "wait_small.png", "history_queued_bg", "data_queued.png" ),
]

if __name__ == "__main__":
    print "This script is no longer used for generating stylesheets. Please use the Makefile instead"

    # Old code for processing stylesheets
    """
    if len(sys.argv) > 1: # has params
        ini_file, out_dir = sys.argv[1:]
    else:
        cwd = os.getcwd() # default settings
        ini_file, out_dir = cwd + "/blue_colors.ini", cwd + "/blue"

    for in_file, out_file in templates:
        print in_file ,"->", out_file
        subprocess.call( "./process_css.py %s shared_images:../images %s < %s > %s" % ( ini_file, out_dir, in_file, os.path.join( out_dir, out_file ) ), shell=True )
    """
  
# Old code for processing images, long disabled, though images are still used. 
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


