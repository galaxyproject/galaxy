#!/usr/bin/env python

# Script requires handlebars compiler be installed; use node package manager 
# to install handlebars.

import sys

from glob import glob
from subprocess import call
from shutil import copyfile
from os import path

cmd = "handlebars %s -f compiled/%s.js"

# If specific scripts specified on command line, just pack them, otherwise pack
# all.

if len( sys.argv ) > 1:
    to_pack = sys.argv[1:]
else:
    to_pack = glob( "*.handlebars" )
    
for fname in to_pack:
    fname_base = path.splitext( path.split( fname )[1] )[0]
    print "%s --> compiled/%s.js" % ( fname, fname_base )
    out = call( cmd % ( fname, fname_base ), shell=True )
