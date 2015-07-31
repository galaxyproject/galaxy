"""
Bootstrap the Galaxy framework.

This should not be called directly!  Use the run.sh script in Galaxy's
top level directly.
"""

import os
import sys

# ensure supported version
from check_python import check_python
try:
    check_python()
except:
    sys.exit( 1 )

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )  # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs

if 'LOG_TEMPFILES' in os.environ:
    from log_tempfile import TempFile
    _log_tempfile = TempFile()

eggs.require( "Paste" )
eggs.require( "PasteDeploy" )

from galaxy.util.pastescript import serve
serve.run()
