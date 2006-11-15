# Author: David Goodger, Dmitry Jemerov
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 856 $
# Date: $Date: 2002-10-24 03:01:53 +0200 (Thu, 24 Oct 2002) $
# Copyright: This module has been placed in the public domain.

"""
Directives for references and targets.
"""

__docformat__ = 'reStructuredText'

from docutils import nodes
from docutils.transforms import references


def target_notes(name, arguments, options, content, lineno,
                 content_offset, block_text, state, state_machine):
    """Target footnote generation."""
    pending = nodes.pending(references.TargetNotes)
    state_machine.document.note_pending(pending)
    nodelist = [pending]
    return nodelist
