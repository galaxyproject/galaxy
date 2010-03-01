#!/usr/bin/env python

import os, sys

assert sys.version_info[:2] >= ( 2, 4 )

lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "lib" ) )
sys.path.append( lib )

import galaxy
import pkg_resources
print pkg_resources.get_platform()
