#!/usr/bin/env python
"""
Example usage:
./library_upload_from_import_dir.py <key> http://127.0.0.1:8080/api/libraries/dda47097d9189f15/contents Fdda47097d9189f15 auto /Users/EnisAfgan/projects/pprojects/galaxy/lib_upload_dir ?
"""
from __future__ import print_function

import os
import sys

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
    print('usage: %s key url folder_id file_type server_dir dbkey' % os.path.basename( sys.argv[0] ))
    sys.exit( 1 )

submit( sys.argv[1], sys.argv[2], data )
