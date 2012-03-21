#!/usr/bin/env python

import sys, os

ini_file, out_dir = "blue_colors.ini", "blue"
if len(sys.argv) > 1: 
    ini_file, out_dir = sys.argv[1:]

cmd = "make INI=%s OUT=%s" % ( ini_file, out_dir )

print """NOTE: This script is no longer used for generating stylesheets.
Invoking '%s' instead""" % cmd

os.system( cmd )



