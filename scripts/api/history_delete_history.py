#!/usr/bin/env python

import os, sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import delete

try:
    assert sys.argv[2]
except IndexError:
    print 'usage: %s key url [purge (true/false)] ' % os.path.basename( sys.argv[0] )
    sys.exit( 1 )
try:
    data = {}
    data[ 'purge' ] = sys.argv[3]
except IndexError:
    pass

delete( sys.argv[1], sys.argv[2], data )
