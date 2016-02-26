#!/usr/bin/env python
import os
import sys

assert sys.version_info[:2] >= ( 2, 4 )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir, "lib" ) )
sys.path.insert( 1, lib )

import pkg_resources
print pkg_resources.get_platform()
