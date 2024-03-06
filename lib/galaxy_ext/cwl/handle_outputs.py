"""
"""

import logging
import os
import sys

# insert *this* galaxy before all others on sys.path
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))

from galaxy.tool_util.cwl import handle_outputs

logging.basicConfig()
log = logging.getLogger(__name__)


def relocate_dynamic_outputs():
    handle_outputs()
