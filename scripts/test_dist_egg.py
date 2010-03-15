#!/usr/bin/env python
"""
A crude script for minimal "testing" of dist eggs (require and import).  It may
not work on all zipped eggs.  It may be easiest to just customize this script
for whatever egg you want to test.

usage: test_dist_egg.py <egg_name>
"""
import os, sys, logging, subprocess

try:
    assert sys.argv[1]
except:
    print __doc__
    sys.exit( 1 )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..', 'lib' ) )
sys.path.insert( 0, lib )

if sys.argv[1].endswith( '.egg' ):

    egg = sys.argv[1]
    egg_name = os.path.basename( egg ).split( '-' )[0]
    sys.path.insert( 0, egg )

    import pkg_resources
    pkg_resources.require( egg_name )
    provider = pkg_resources.get_provider( egg_name )
    importables = provider.get_metadata('top_level.txt').splitlines()

    for importable in importables:
        mod = __import__( importable )
        assert os.path.dirname( mod.__path__[0] ) == os.path.dirname( provider.module_path )
        print "OK"

    sys.exit( 0 )

else:

    build_dir = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), 'scramble', 'build' )
    if os.path.exists( build_dir ):
        raise Exception( 'Build dir must be removed before testing: %s' % build_dir )

    name = sys.argv[1]

    from galaxy.eggs.dist import DistScrambleCrate
    
    c = DistScrambleCrate()
    
    for egg in c[name]:
        print 'Checking %s %s for %s on %s' % ( name, egg.version, egg.platform, egg.build_host )
        p = subprocess.Popen( 'ssh %s %s %s %s %s' % ( egg.build_host, egg.python, os.path.abspath( __file__ ), egg.distribution.location, egg.platform ), shell=True )
        p.wait()
