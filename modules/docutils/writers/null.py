# Author: David Goodger
# Contact: goodger@python.org
# Revision: $Revision: 3246 $
# Date: $Date: 2005-04-23 21:23:21 +0200 (Sat, 23 Apr 2005) $
# Copyright: This module has been placed in the public domain.

"""
A do-nothing Writer.
"""

from docutils import writers


class Writer(writers.Writer):

    supported = ('null',)
    """Formats this writer supports."""

    config_section = 'null writer'
    config_section_dependencies = ('writers',)

    def translate(self):
        pass
