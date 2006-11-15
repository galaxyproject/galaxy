#!/usr/bin/env python2.4

import pkg_resources; 
pkg_resources.require( "PasteScript" )

from paste.script import command
command.run()
