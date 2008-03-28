#!/usr/bin/env python

import sys

assert sys.version_info[:2] >= ( 2, 4 )

import pkg_resources; 
pkg_resources.require( "PasteScript" )

from paste.script import command
command.run()
