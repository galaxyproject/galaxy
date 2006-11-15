# Author: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 3353 $
# Date: $Date: 2005-05-19 02:49:14 +0200 (Thu, 19 May 2005) $
# Copyright: This module has been placed in the public domain.

"""
Standalone file Reader for the reStructuredText markup syntax.
"""

__docformat__ = 'reStructuredText'


import sys
from docutils import frontend, readers
from docutils.transforms import frontmatter, references


class Reader(readers.Reader):

    supported = ('standalone',)
    """Contexts this reader supports."""

    document = None
    """A single document tree."""

    settings_spec = (
        'Standalone Reader',
        None,
        (('Disable the promotion of a lone top-level section title to '
          'document title (and subsequent section title to document '
          'subtitle promotion; enabled by default).',
          ['--no-doc-title'],
          {'dest': 'doctitle_xform', 'action': 'store_false', 'default': 1,
           'validator': frontend.validate_boolean}),
         ('Disable the bibliographic field list transform (enabled by '
          'default).',
          ['--no-doc-info'],
          {'dest': 'docinfo_xform', 'action': 'store_false', 'default': 1,
           'validator': frontend.validate_boolean}),
         ('Activate the promotion of lone subsection titles to '
          'section subtitles (disabled by default).',
          ['--section-subtitles'],
          {'dest': 'sectsubtitle_xform', 'action': 'store_true', 'default': 0,
           'validator': frontend.validate_boolean}),
         ('Deactivate the promotion of lone subsection titles.',
          ['--no-section-subtitles'],
          {'dest': 'sectsubtitle_xform', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ))

    config_section = 'standalone reader'
    config_section_dependencies = ('readers',)

    default_transforms = (references.Substitutions,
                          references.PropagateTargets,
                          frontmatter.DocTitle,
                          frontmatter.SectionSubTitle,
                          frontmatter.DocInfo,
                          references.AnonymousHyperlinks,
                          references.IndirectHyperlinks,
                          references.Footnotes,
                          references.ExternalTargets,
                          references.InternalTargets,)
