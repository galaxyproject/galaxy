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

from galaxy.eggs import Crate, EggNotFetchable
import pkg_resources

c = Crate()
try:
    c.platform = sys.argv[2]
except:
    pass
try:
    if len( sys.argv ) == 1:
        c.resolve() # Only fetch eggs required by the config
    elif sys.argv[1] == 'all':
        c.resolve( all=True ) # Fetch everything
    else:
        # Fetch a specific egg
        name = sys.argv[1]
        try:
            egg = c[name]
        except:
            print "error: %s not in eggs.ini" % name
            sys.exit( 1 )
        dist = egg.resolve()[0]
        print "%s %s is installed at %s" % ( dist.project_name, dist.version, dist.location )
except EggNotFetchable, e:
    try:
        assert sys.argv[1] != 'all'
        egg = e.eggs[0]
        print "%s %s couldn't be downloaded automatically.  You can try" % ( egg.name, egg.version )
        print "building it by hand with:"
        print "  python scripts/scramble.py %s"
    except ( AssertionError, IndexError ):
        print "One or more of the python eggs necessary to run Galaxy couldn't be"
        print "downloaded automatically.  You can try building them by hand (all"
        print "at once) with:"
        print "  python scripts/scramble.py"
        print "Or individually:"
        for egg in e.eggs:
            print "  python scripts/scramble.py %s" % egg.name
    sys.exit( 1 )
sys.exit( 0 )
