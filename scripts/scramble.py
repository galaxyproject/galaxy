"""
usage: scramble.py <egg_name> [platform]
    egg_name - The name of an egg to build, as defined in eggs.ini
    platform - An optional platform to build the egg for.

The platform option is mostly intended for the Galaxy developers who distribute
eggs via the Galaxy Eggs site.  Please see the comments in eggs.ini for more
information about using the platform option.
"""
import os, sys
from eggs import scramble

if len( sys.argv ) < 2:
    print __doc__
    sys.exit( 1 )

#scramble_lib = os.path.join( os.path.dirname( sys.argv[0] ), "scramble", "lib" )
#sys.path.append( scramble_lib )

#try:
#    from setuptools import *
#except:
#    from ez_setup import use_setuptools
#    use_setuptools( download_delay=8, to_dir=scramble_lib )
#    from setuptools import *

if len( sys.argv ) == 3:
    plat = sys.argv[2]
else:
    plat = "default"

scramble( sys.argv[1], plat )
