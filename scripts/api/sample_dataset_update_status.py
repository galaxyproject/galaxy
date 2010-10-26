#!/usr/bin/env python


import os, sys, traceback
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import display
from common import submit
from common import update
try:
    data = {}
    data[ 'update_type' ] = 'sample_dataset_transfer_status'
    data[ 'sample_dataset_ids' ] = sys.argv[3].split(',')
    data[ 'new_status' ] = sys.argv[4]
except IndexError:
    print 'usage: %s key url sample_dataset_ids new_state [error msg]' % os.path.basename( sys.argv[0] )
    sys.exit( 1 )
try:
    data[ 'error_msg' ] = sys.argv[5]
except IndexError:
    data[ 'error_msg' ] = ''    
print data
update( sys.argv[1], sys.argv[2], data, return_formatted=True )
