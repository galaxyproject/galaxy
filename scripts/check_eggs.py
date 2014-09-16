#!/usr/bin/env python
"""
Compares local dependency eggs to those in eggs.ini, displaying a warning if
any are out of date.

usage: check_eggs.py [options]
"""

import os, sys, logging
from optparse import OptionParser

parser = OptionParser()
parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (config/galaxy.ini)', default='config/galaxy.ini' )
parser.add_option( '-q', '--quiet', dest='quiet', action="store_true", help='Quiet (no output, only set return code)', default=False )
( options, args ) = parser.parse_args()

if not os.path.exists( options.config ):
    print "Config file does not exist (see 'python %s --help'): %s" % ( sys.argv[0], options.config )
    sys.exit( 1 )

root = logging.getLogger()
root.setLevel( 10 )
root.addHandler( logging.StreamHandler( sys.stdout ) )

config_arg = ''
if options.config != 'config/galaxy.ini':
    config_arg = '-c %s' % options.config

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs import Crate

c = Crate( options.config )
if c.config_missing:
    if not options.quiet:
        print "Some of your Galaxy eggs are out of date.  Please update them"
        print "by running:"
        print "  python scripts/fetch_eggs.py %s" % config_arg
    sys.exit( 1 )
sys.exit( 0 )
