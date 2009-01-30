#!/usr/bin/env python

import os, sys

assert sys.version_info[:2] >= ( 2, 4 )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs import get_platform
print get_platform()
print get_platform( True )
