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

from galaxy.eggs import *

c = Crate()
c.parse()
galaxy_config = GalaxyConfig()
ignore = []
for name in c.get_names():
    if not galaxy_config.check_conditional( name ):
        ignore.append( name )
if not c.find( ignore=ignore ):
    print "Some of your Galaxy eggs are out of date.  Please update them"
    print "by running:"
    print "  python scripts/fetch_eggs.py"
    sys.exit( 1 )
