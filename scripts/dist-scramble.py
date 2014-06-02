"""
Scrambles eggs for distribution on multiple platforms.

(from https://wiki.galaxyproject.org/Admin/Config/Eggs )
This is mostly designed for use by Galaxy Developers at Penn State who are
building eggs for distribution via the Galaxy Eggs distribution site.
dist-scramble.py uses the dist-eggs.ini config file to determine what platforms
to build for, and which hosts to build on.

dist-scramble.py works the same way as scramble.py: ::

% python scripts/dist-scramble.py galaxy_egg

Called with only the egg argument, dist-scramble.py will build for all the
platforms under the all group in its config file (for platform-specific eggs)
or the noplatform group (for platform-inspecific eggs). The [[hosts]|section
contains information about which hosts will be used for building on each desired
platform. If you don't want to build for all the platforms listed under the all
group, you can add a platform argument (any lvalue in the [hosts]] or [groups]
section is valid): ::

% python scripts/dist-scramble.py galaxy_egg linux

The platform argument is ignored for platform-inspecific eggs. An assumption is
made that your Galaxy distribution is located at the same place on all of the
hosts on which you're building (i.e. via a network filesystem).

Once dist-scramble.py finishes, it will output a list of platforms on which it
failed to scramble the egg. Successful eggs will be put in a new dist-eggs
subdirectory of your Galaxy distribution. These eggs can then be copied to your
distribution site.
"""

import os, sys, logging
from optparse import OptionParser

parser = OptionParser()
parser.add_option( '-e', '--egg-name', dest='egg_name', help='Egg name (as defined in eggs.ini) to scramble (required)' )
parser.add_option( '-p', '--platform', dest='platform', help='Scramble for a specific platform (by default, eggs are scrambled for all platforms, see dist-eggs.ini for platform names)' )
( options, args ) = parser.parse_args()

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..', 'lib' ) )
sys.path.append( lib )

from galaxy.eggs.dist import DistScrambleCrate, ScrambleFailure
from galaxy.eggs import EggNotFetchable

if not options.egg_name:
    print "ERROR: You must specify an egg to scramble (-e)"
    parser.print_help()
    sys.exit( 1 )

if options.platform:
    c = DistScrambleCrate( None, options.platform )
else:
    c = DistScrambleCrate( None )

try:
    eggs = c[options.egg_name]
except:
    print "ERROR: %s not in eggs.ini" % options.egg_name
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
