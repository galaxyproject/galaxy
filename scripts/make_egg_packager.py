#!/usr/bin/env python

import os, sys, logging, shutil
from optparse import OptionParser

parser = OptionParser()
parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (universe_wsgi.ini)', default='universe_wsgi.ini' )
parser.add_option( '-p', '--platform', dest='platform', help='Fetch for a specific platform (by default, eggs are fetched for *this* platform' )
( options, args ) = parser.parse_args()

if not os.path.exists( options.config ):
    print "Config file does not exist (see 'python %s --help'): %s" % ( sys.argv[0], options.config )
    sys.exit( 1 )

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs import Crate, EggNotFetchable, py
import pkg_resources

try:
    assert options.platform
    platform = options.platform
    c = Crate( options.config, platform = platform )
    print "Platform forced to '%s'" % platform
except:
    platform = '-'.join( ( py, pkg_resources.get_platform() ) )
    c = Crate( options.config )
    print "Using Python interpreter at %s, Version %s" % ( sys.executable, sys.version )
    print "This platform is '%s'" % platform
    print "Override with:"
    print "  make_egg_packager.py <forced-platform>"

shutil.copy( os.path.join( os.path.dirname( __file__ ), 'egg_packager_template.py' ), 'egg_packager-%s.py' % platform )

packager = open( 'egg_packager-%s.py' % platform, 'a' )
packager.write( "py = '%s'\n" % py )
packager.write( "url = '%s'\n" % c.repo )
packager.write( "platform = '%s'\n" % platform )
packager.write( "dists = [\n" )

for egg in c.all_eggs:
    if egg.name in c.no_auto:
        continue
    packager.write( "          Distribution( '%s', '%s', '%s', '%s', '%s' ),\n" % ( egg.distribution.egg_name(), egg.distribution.project_name, egg.distribution.version, egg.distribution.py_version, egg.distribution.platform ) )

packager.write( """]

for d in dists:
    e = Egg( d )
    if not e.fetch( None ):
        failures.append( e )

if failures:
    print ""
    print "Failed:"
    for e in failures:
        print e.distribution.project_name
else:
    create_zip()
clean()
""" ) 

print "Completed packager is 'egg_packager-%s.py'.  To" % platform
print "fetch eggs, please copy this file to a system with internet access and run"
print "with:"
print "  python egg_packager-%s.py" % platform
