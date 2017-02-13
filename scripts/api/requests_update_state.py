#!/usr/bin/env python
from __future__ import print_function

import os
import sys

from common import update

try:
    data = {}
    data[ 'update_type' ] = 'request_state'
except IndexError:
    print('usage: %s key url' % os.path.basename( sys.argv[0] ))
    sys.exit( 1 )

update( sys.argv[1], sys.argv[2], data, return_formatted=True )
