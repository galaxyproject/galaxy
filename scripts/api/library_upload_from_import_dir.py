#!/usr/bin/env python

import os, sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit

try:
    data = {}
    data[ 'folder_id' ] = sys.argv[3]
    data[ 'file_type' ] = sys.argv[4]
    data[ 'server_dir' ] = sys.argv[5]
    data[ 'dbkey' ] = sys.argv[6]
    data[ 'upload_option' ] = 'upload_directory'
    data[ 'create_type' ] = 'file'
except IndexError:
    print 'usage: %s key url folder_id file_type server_dir dbkey' % os.path.basename( sys.argv[0] )
    sys.exit( 1 )

submit( sys.argv[1], sys.argv[2], data )
