"""
usage: scramble.py [egg_name]
    With no arguments, scrambles all eggs necessary according to the
    settings in universe_wsgi.ini.
  egg_name - Scramble only this egg (as defined in eggs.ini) or 'all'
    for all eggs (even those not required by your settings).
"""
import os, sys, logging

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs import Crate, GalaxyConfig

c = Crate()
c.parse()
if len( sys.argv ) == 1:
    galaxy_config = GalaxyConfig()
    ignore = []
    for name in c.get_names():
        if not galaxy_config.check_conditional( name ):
            ignore.append( name )
    c.scramble( ignore=ignore )
else:
    if sys.argv[1] == 'all':
        c.scramble()
    else:
        egg = c.get( sys.argv[1] )
        if egg is None:
            print "error: %s not in eggs.ini" % sys.argv[1]
            sys.exit( 1 )
        egg.scramble()
