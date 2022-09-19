#!/usr/bin/env python

# Author: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 1.2 $
# Date: $Date: 2004/03/28 15:39:27 $
# Copyright: This module has been placed in the public domain.

"""
A minimal front end to the Docutils Publisher, producing HTML.
"""

try:
    import locale

    locale.setlocale(locale.LC_ALL, "")
except Exception:
    pass

from docutils.core import (
    default_description,
    publish_cmdline,
)

description = "Generates (X)HTML documents from standalone reStructuredText " "sources.  " + default_description

publish_cmdline(writer_name="html", description=description)
