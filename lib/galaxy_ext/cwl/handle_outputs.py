"""
"""

import logging
import os
import sys

# insert *this* galaxy before all others on sys.path
sys.path.insert( 1, os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir, os.pardir ) ) )

from galaxy.tools.cwl import handle_outputs

# ensure supported version
assert sys.version_info[:2] >= ( 2, 6 ) and sys.version_info[:2] <= ( 2, 7 ), 'Python version must be 2.6 or 2.7, this is: %s' % sys.version

logging.basicConfig()
log = logging.getLogger( __name__ )


def relocate_dynamic_outputs():
    handle_outputs()
