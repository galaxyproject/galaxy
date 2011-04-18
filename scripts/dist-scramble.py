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

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..', 'lib' ) )
sys.path.append( lib )

from galaxy.eggs.dist import DistScrambleCrate, ScrambleFailure
from galaxy.eggs import EggNotFetchable

if len( sys.argv ) > 3 or len( sys.argv ) < 2:
    print __doc__
    sys.exit( 1 )
elif len( sys.argv ) == 3:
    c = DistScrambleCrate( sys.argv[2] )
else:
    c = DistScrambleCrate()

try:
    eggs = c[sys.argv[1]]
except:
    print "error: %s not in eggs.ini" % sys.argv[1]
    sys.exit( 1 )
failed = []
for egg in eggs:
    try:
        for dependency in egg.dependencies:
            print "Checking %s on %s dependency: %s" % ( egg.name, egg.platform, dependency )
            # this could be in a better data structure...
            dep = filter( lambda x: x.platform == egg.platform, c[dependency] )[0]
            if not os.path.exists( dep.distribution.location ):
                dep.fetch( dep.distribution.as_requirement() )
    except EggNotFetchable, e:
        degg = e.eggs[0]
        print "%s build dependency %s %s %s couldn't be" % ( egg.name, degg.name, degg.version, degg.platform )
        print "downloaded automatically.  There isn't really a graceful"
        print "way to handle this when dist-scrambling."
        failed.append( egg.platform )
        continue
    try:
        egg.scramble()
    except ScrambleFailure:
        failed.append( egg.platform )
if len( failed ):
    print ""
    print "Scramble failed to build eggs on the following platforms (more details"
    print "can be found by reviewing the output above):"
    print "\n".join( failed )
