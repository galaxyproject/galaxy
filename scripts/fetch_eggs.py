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
    galaxy_config = GalaxyConfig()
    names = []
    if len( sys.argv ) == 1:
        names = c.get_names()
    elif sys.argv[1] == 'all':
        names = galaxy_config.always_conditional
    else:
        # Fetch a specific egg
        egg = c.get( sys.argv[1] )
        if egg is None:
            print "error: %s not in eggs.ini" % sys.argv[1]
            sys.exit( 1 )
        egg.fetch()
        sys.exit( 0 )
    ignore = filter( lambda x: not galaxy_config.check_conditional( x ), list( names ) )
    c.fetch( ignore )
except EggNotFetchable, e:
    print "One or more of the python eggs necessary to run Galaxy couldn't be"
    print "downloaded automatically.  You may want to try building them by"
    print "hand with:"
    for egg in e.eggs:
        print "  python scripts/scramble.py %s" % egg
    sys.exit( 1 )
except PlatformNotSupported, e:
    print "Your platform (%s) is not supported." % e
    print "Pre-built galaxy eggs are not available from the Galaxy developers for"
    print "your platform.  You may be able to build them by hand with:"
    print "  python scripts/scramble.py"
    sys.exit( 1 )
