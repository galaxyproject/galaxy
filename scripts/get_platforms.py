#!/usr/bin/env python

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

from galaxy.eggs import get_platform, get_noplatform
print get_noplatform()
print get_platform( platform=True )
