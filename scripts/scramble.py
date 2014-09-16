import os, sys, logging
from optparse import OptionParser

parser = OptionParser()
parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (config/galaxy.ini)', default='config/galaxy.ini' )
parser.add_option( '-e', '--egg-name', dest='egg_name', help='Egg name (as defined in eggs.ini) to fetch, or "all" for all eggs, even those not needed by your configuration' )
( options, args ) = parser.parse_args()

if not os.path.exists( options.config ):
    print "Config file does not exist (see 'python %s --help'): %s" % ( sys.argv[0], options.config )
    sys.exit( 1 )

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs.scramble import ScrambleCrate, ScrambleFailure, EggNotFetchable

c = ScrambleCrate( options.config )

try:
    if not options.egg_name:
        eggs = c.scramble()
    elif options.egg_name == 'all':
        c.scramble( all=True )
    else:
        # Scramble a specific egg
        name = options.egg_name
        try:
            egg = c[name]
        except:
            print "error: %s not in eggs.ini" % name
            sys.exit( 1 )
        for dependency in egg.dependencies:
            config_arg = ''
            if options.config != 'config/galaxy.ini':
                config_arg = '-c %s' % options.config
            print "Checking %s dependency: %s" % ( egg.name, dependency )
            try:
                c[dependency].require()
            except EggNotFetchable, e:
                degg = e.eggs[0]
                print "%s build dependency %s %s couldn't be downloaded" % ( egg.name, degg.name, degg.version )
                print "automatically.  You can try building it by hand with:"
                print "  python scripts/scramble.py %s-e %s" % ( config_arg, degg.name )
                sys.exit( 1 )
        egg.scramble()
        sys.exit( 0 )
except ScrambleFailure, e:
    if len( e.eggs ) == 1:
        raise
    else:
        print 'Scrambling the following eggs failed:\n ',
        print '\n  '.join( [ egg.name for egg in e.eggs ] )
    sys.exit( 1 )
