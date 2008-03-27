import sys
from eggs import *

config_eggs = ConfigEggs()
galaxy_eggs = GalaxyEggs()

# "all" argument used to fetch all eggs, for buildbot
if len( sys.argv ) == 2:
    if sys.argv[1] == "all":
        galaxy_config = "all"
    else:
        print "Unknown argument:", sys.argv[1]
        sys.exit( 1 )
else:
    galaxy_config = GalaxyConfig()

missing_eggs = get_missing_eggs( config_eggs, galaxy_eggs, galaxy_config )
if len( missing_eggs ) != 0:
    ret = fetch_eggs( config_eggs.repo, missing_eggs )
    if ret == []:
        print "Eggs fetched successfully"
        sys.exit( 0 )
    else:
        print ""
        print 'fetch_eggs.py was unable to download some eggs.  You may have success'
        print '"scrambling" them yourself:'
        print ""
        for name in ret:
            print " ", sys.executable, os.path.join( os.path.dirname( sys.argv[0] ), "scramble.py" ), name
        print ""
        sys.exit( 1 )
else:
    print "All eggs are up to date for this revision of Galaxy"
sys.exit( 0 )
