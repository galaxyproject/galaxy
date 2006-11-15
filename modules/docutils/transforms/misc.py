# Author: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 3155 $
# Date: $Date: 2005-04-02 23:57:06 +0200 (Sat, 02 Apr 2005) $
# Copyright: This module has been placed in the public domain.

"""
Miscellaneous transforms.
"""

__docformat__ = 'reStructuredText'

from docutils import nodes
from docutils.transforms import Transform, TransformError


class CallBack(Transform):

    """
    Inserts a callback into a document.  The callback is called when the
    transform is applied, which is determined by its priority.

    For use with `nodes.pending` elements.  Requires a ``details['callback']``
    entry, a bound method or function which takes one parameter: the pending
    node.  Other data can be stored in the ``details`` attribute or in the
    object hosting the callback method.
    """

    default_priority = 990

    def apply(self):
        pending = self.startnode
        pending.details['callback'](pending)
        pending.parent.remove(pending)


class ClassAttribute(Transform):

    """
    Move the "class" attribute specified in the "pending" node into the
    immediately following non-comment element.
    """

    default_priority = 210

    def apply(self):
        pending = self.startnode
        parent = pending.parent
        child = pending
        while parent:
            # Check for appropriate following siblings:
            for index in range(parent.index(child) + 1, len(parent)):
                element = parent[index]
                if (isinstance(element, nodes.Invisible) or
                    isinstance(element, nodes.system_message)):
                    continue
                element['classes'] += pending.details['class']
                pending.parent.remove(pending)
                return
            else:
                # At end of section or container; apply to sibling
                child = parent
                parent = parent.parent
        error = self.document.reporter.error(
            'No suitable element following "%s" directive'
            % pending.details['directive'],
            nodes.literal_block(pending.rawsource, pending.rawsource),
            line=pending.line)
        pending.parent.replace(pending, error)
