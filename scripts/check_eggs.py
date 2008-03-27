import os, sys, pickle, subprocess
from eggs import *

config_eggs = ConfigEggs()
galaxy_eggs = GalaxyEggs()
galaxy_config = GalaxyConfig()
pickle_name = ".eggs.pickle"

if os.environ.has_key( "GALAXY_IGNORE_EGGS" ):
    ignore = int( os.environ[ "GALAXY_IGNORE_EGGS" ] )
else:
    ignore = False

print "Checking Galaxy eggs"
missing_eggs = get_missing_eggs( config_eggs, galaxy_eggs, galaxy_config )
if len( missing_eggs ) != 0:
    if ignore:
        # create the pickle if necessary
        if not os.access( pickle_name, os.F_OK ):
            dict = {}
            f = open( pickle_name, "w" )
            pickle.dump( dict, f )
            f.close()
        # check the last run rev for this arch
        f = open( pickle_name, "r" )
        last_revs = pickle.load( f )
        f.close()
        entries = os.path.abspath( os.path.join( os.path.dirname( sys.argv[0] ), "..", ".svn", "entries" ) )
        f = open( entries, "r" )
        for i in range(0, 4):
            this_rev = f.readline().strip()
        f.close()
        plat = get_full_platform()
        if last_revs.has_key( plat ):
            last_rev = last_revs[plat]
        else:
            last_rev = None
        if this_rev == last_rev:
            print ""
            print "WARNING: Some eggs are out of date or missing, but"
            print "GALAXY_IGNORE_EGGS is set, so Galaxy will start anyway."
            print ""
            sys.exit( 0 )
        else:
            print ""
            print "ERROR:"
            print ""
            print "The environment variable GALAXY_IGNORE_EGGS has been set to"
            print "force Galaxy to start, regardless of the fact that some required"
            print "eggs are missing or outdated.  However, this revision of Galaxy has"
            print "changed since the last time you ran it on this platform (probably"
            print "due to an 'svn update').  Please be aware that running a new"
            print "revision on an outdated module can cause unknown problems (if it"
            print "works at all)."
            print ""
            print "Galaxy startup will terminate now, but if you execute run.sh"
            print "again, startup will proceed normally."
            print ""
            last_revs[plat] = this_rev
            f = open( pickle_name, "w" )
            pickle.dump( last_revs, f )
            f.close()
            sys.exit( 1 )
    else:
        print ""
        print "ERROR:"
        print ""
        print "Your Galaxy eggs are missing or out of date.  Please run:"
        print ""
        print " ", sys.executable, os.path.join( os.path.dirname( sys.argv[0] ), "fetch_eggs.py" )
        print ""
        print "to download the correct eggs for this version of Galaxy."
        print ""
        sys.exit( 1 )

# if we made it this far, we're good.
print "All eggs are up to date for this revision of Galaxy"
sys.exit( 0 )
