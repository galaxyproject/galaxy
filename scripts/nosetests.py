#!/usr/bin/env python
# EASY-INSTALL-ENTRY-SCRIPT: 'nose','console_scripts','nosetests'
#__requires__ = 'nose'
import os, sys

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs
eggs.require( 'nose' )
eggs.require( 'NoseHTML' )

from pkg_resources import load_entry_point

assert sys.version_info[:2] >= ( 2, 4 )

sys.exit(
   load_entry_point('nose', 'console_scripts', 'nosetests')()
)
