#!/usr/bin/env python

import os, sys, urllib2
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import display

try:
    display( *sys.argv[1:3] )
except TypeError:
    print 'usage: %s key url' % os.path.basename( sys.argv[0] )
    sys.exit( 1 )
except urllib2.URLError, e:
    print str(e)
    sys.exit( 1 )
