"""
Classes for all files related to machine learning
"""

from galaxy.datatypes import data
from galaxy.datatypes.metadata import MetadataElement

import os
import logging

log = logging.getLogger(__name__)

class tensorflow(data.Text):
    """
        Class for tensorflow checkpoint files
    """
    file_ext = "ckpt"
