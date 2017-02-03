#!/usr/bin/env python
"""
# ---------------------------------------------- #
# PARKLAB, Author: RPARK
API example script for deleting workflows
# ---------------------------------------------- #

Example calls:
python workflow_delete.py <api_key> <galaxy_url>/api/workflows/<workflow id> True
"""
from __future__ import print_function

import os
import sys

from common import delete

try:
    assert sys.argv[2]
except IndexError:
    print('usage: %s key url [purge (true/false)] ' % os.path.basename( sys.argv[0] ))
    sys.exit( 1 )
try:
    data = {}
    data[ 'purge' ] = sys.argv[3]
except IndexError:
    pass

delete( sys.argv[1], sys.argv[2], data )
