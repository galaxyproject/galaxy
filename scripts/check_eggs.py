#! /usr/bin/python
"""
usage: check_eggs.py
"""
import os, sys, logging

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

try:
    assert sys.argv[1] == 'quiet'
    quiet = True
except:
    quiet = False

from galaxy.eggs import Crate

c = Crate()
if c.config_missing:
    if not quiet:
        print "Some of your Galaxy eggs are out of date.  Please update them"
        print "by running:"
        print "  python scripts/fetch_eggs.py"
    sys.exit( 1 )
sys.exit( 0 )
