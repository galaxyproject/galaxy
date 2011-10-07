#!/usr/bin/env python
"""
Generic PUT/update script

usage: create.py key url [key=value ...]
"""

import os, sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import update

data = {}
for k, v in [ kwarg.split('=', 1) for kwarg in sys.argv[3:]]:
    data[k] = v

update( sys.argv[1], sys.argv[2], data )
