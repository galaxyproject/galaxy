"""
Bootstrap the Galaxy framework.

This should not be called directly!  Use the run.sh script in Galaxy's
top level directly.
"""

import os, sys

assert sys.version_info[:2] >= ( 2, 4 )

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
import pkg_resources

pkg_resources.require( "PasteScript" )

from paste.script import command
command.run()
