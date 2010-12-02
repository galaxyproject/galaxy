#!/usr/bin/env python

import os, sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit

try:
    data = {}
    data[ 'xml_text' ] = open( sys.argv[3] ).read()
except IndexError:
    print 'usage: %s key url form_xml_description_file' % os.path.basename( sys.argv[0] )
    sys.exit( 1 )


submit( sys.argv[1], sys.argv[2], data )
