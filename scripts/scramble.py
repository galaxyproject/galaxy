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

from galaxy.eggs.scramble import ScrambleCrate, ScrambleFailure

c = ScrambleCrate()

try:
    if len( sys.argv ) == 1:
        eggs = c.scramble()
    elif sys.argv[1] == 'all':
        c.scramble( all=True )
    else:
        # Scramble a specific egg
        name = sys.argv[1]
        try:
            egg = c[name]
        except:
            print "error: %s not in eggs.ini" % name
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
