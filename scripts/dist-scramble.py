"""
usage: dist-scramble.py <egg_name> [platform]
  egg_name - The egg to scramble (as defined in eggs.ini)
  platform - The platform to scramble on (as defined in
             dist-eggs.ini).  Leave blank for all.
             Platform-inspecific eggs ignore this argument.
"""
import os, sys, logging

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs import DistCrate

if len( sys.argv ) > 3 or len( sys.argv ) < 2:
    print __doc__
    sys.exit( 1 )
elif len( sys.argv ) == 3:
    c = DistCrate( sys.argv[2] )
else:
    c = DistCrate()

c.parse()
egg_list = c.get( sys.argv[1] )
if egg_list is None:
    print "error: %s not in eggs.ini" % sys.argv[1]
    sys.exit( 1 )
failed = []
for egg in egg_list:
    if not egg.scramble():
        failed.append( egg.platform['galaxy'] )
if len( failed ):
    print ""
    print "Scramble failed to build eggs on the following platforms (more details"
    print "can be found by reviewing the output above):"
    print "\n".join( failed )
