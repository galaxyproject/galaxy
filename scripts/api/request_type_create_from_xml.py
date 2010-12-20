#!/usr/bin/env python

import os, sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit

try:
    data = {}
    data[ 'request_form_id' ] = sys.argv[3]
    data[ 'sample_form_id' ] = sys.argv[4]
    data[ 'sequencer_id' ] = sys.argv[5]
    data[ 'xml_text' ] = open( sys.argv[6] ).read()
except IndexError:
    print 'usage: %s key url request_form_id sample_form_id request_type_xml_description_file [access_role_ids,]' % os.path.basename( sys.argv[0] )
    sys.exit( 1 )
try:
    data[ 'role_ids' ] = [ i for i in sys.argv[7].split( ',' ) if i ]
except IndexError:
    data[ 'role_ids' ] = []

submit( sys.argv[1], sys.argv[2], data )
