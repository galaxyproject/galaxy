"""
usage: fetch_eggs.py [egg_name] [platform]
    With no arguments, fetches all eggs necessary according to the
    settings in universe_wsgi.ini.
  egg_name - Fetch only this egg (as defined in eggs.ini) or 'all' for
    all eggs (even those not required by your settings).
  platform - Fetch eggs for a specific platform (if not provided, fetch
    eggs for *this* platform).  Useful for fetching eggs for cluster
    nodes which are of a different architecture than the head node.
    Platform name can be determined with the get_platforms.py script.
"""
import os, sys, logging

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs import *

c = Crate()
if len( sys.argv ) == 3:
    c.platform = { 'peak' : sys.argv[2].rsplit('-',1)[0], 'galaxy' : sys.argv[2] }
c.parse()
try:
    if len( sys.argv ) == 1:
        galaxy_config = GalaxyConfig()
        ignore = []
        for name in c.get_names():
            if not galaxy_config.check_conditional( name ):
                ignore.append( name )
        c.fetch( ignore=ignore )
    else:
        if sys.argv[1] == 'all':
            c.fetch()
        else:
            egg = c.get( sys.argv[1] )
            if egg is None:
                print "error: %s not in eggs.ini" % sys.argv[1]
                sys.exit( 1 )
            egg.fetch()
except EggNotFetchable, e:
    print "One of the python eggs necessary to run Galaxy couldn't be downloaded"
    print "automatically.  You may want to try building it by hand with:"
    print "  python scripts/scramble.py %s" % e
    sys.exit( 1 )
except PlatformNotSupported, e:
    print "Your platform (%s) is not supported." % e
    print "Pre-built galaxy eggs are not available from the Galaxy developers for"
    print "your platform.  You may be able to build them by hand with:"
    print "  python scripts/scramble.py"
    sys.exit( 1 )
