#!/usr/bin/env python


import os, sys, traceback
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import update

try:
    data = {}
    data[ 'update_type' ] = 'request_state'
except IndexError:
    print 'usage: %s key url' % os.path.basename( sys.argv[0] )
    sys.exit( 1 )

update( sys.argv[1], sys.argv[2], data, return_formatted=True )

