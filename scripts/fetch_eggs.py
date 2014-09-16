"""
Connects to the Galaxy Eggs distribution site and downloads any eggs needed.

If eggs for your platform are unavailable, fetch_eggs.py will direct you to run
scramble.py.
"""

import os, sys, logging
from optparse import OptionParser

parser = OptionParser()
parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (config/galaxy.ini)', default='config/galaxy.ini' )
parser.add_option( '-e', '--egg-name', dest='egg_name', help='Egg name (as defined in eggs.ini) to fetch, or "all" for all eggs, even those not needed by your configuration' )
parser.add_option( '-p', '--platform', dest='platform', help='Fetch for a specific platform (by default, eggs are fetched for *this* platform' )
( options, args ) = parser.parse_args()

if not os.path.exists( options.config ):
    print "Config file does not exist (see 'python %s --help'): %s" % ( sys.argv[0], options.config )
    sys.exit( 1 )

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs import Crate, EggNotFetchable
import pkg_resources

if options.platform:
    c = Crate( options.config, platform = options.platform )
else:
    c = Crate( options.config )
try:
    if not options.egg_name:
        c.resolve() # Only fetch eggs required by the config
    elif options.egg_name == 'all':
        c.resolve( all=True ) # Fetch everything
    else:
        # Fetch a specific egg
        name = options.egg_name
        try:
            egg = c[name]
        except:
            print "error: %s not in eggs.ini" % name
            sys.exit( 1 )
        dist = egg.resolve()[0]
        print "%s %s is installed at %s" % ( dist.project_name, dist.version, dist.location )
except EggNotFetchable, e:
    config_arg = ''
    if options.config != 'config/galaxy.ini':
        config_arg = '-c %s ' % options.config
    try:
        assert options.egg_name != 'all'
        egg = e.eggs[0]
        print "%s %s couldn't be downloaded automatically.  You can try" % ( egg.name, egg.version )
        print "building it by hand with:"
        print "  python scripts/scramble.py %s-e %s" % ( config_arg, egg.name )
    except ( AssertionError, IndexError ):
        print "One or more of the python eggs necessary to run Galaxy couldn't be"
        print "downloaded automatically.  You can try building them by hand (all"
        print "at once) with:"
        print "  python scripts/scramble.py"
        print "Or individually:"
        for egg in e.eggs:
            print "  python scripts/scramble.py %s-e %s" % ( config_arg, egg.name )
    sys.exit( 1 )
sys.exit( 0 )
