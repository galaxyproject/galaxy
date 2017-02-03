#!/usr/bin/env python
from __future__ import print_function

import os
import sys

from common import submit

try:
    assert sys.argv[2]
except IndexError:
    print('usage: %s key url [name] ' % os.path.basename( sys.argv[0] ))
    sys.exit( 1 )
try:
    data = {}
    data[ 'name' ] = sys.argv[3]
except IndexError:
    pass

submit( sys.argv[1], sys.argv[2], data )
