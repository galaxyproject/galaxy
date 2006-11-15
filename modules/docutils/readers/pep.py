# Author: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 3129 $
# Date: $Date: 2005-03-26 17:21:28 +0100 (Sat, 26 Mar 2005) $
# Copyright: This module has been placed in the public domain.

"""
Python Enhancement Proposal (PEP) Reader.
"""

__docformat__ = 'reStructuredText'


from docutils.readers import standalone
from docutils.transforms import peps, references
from docutils.parsers import rst


class Reader(standalone.Reader):

    supported = ('pep',)
    """Contexts this reader supports."""

    settings_spec = (
        'PEP Reader Option Defaults',
        'The --pep-references and --rfc-references options (for the '
        'reStructuredText parser) are on by default.',
        ())

    config_section = 'pep reader'
    config_section_dependencies = ('readers', 'standalone reader')

    default_transforms = (references.Substitutions,
                          references.PropagateTargets,
                          peps.Headers,
                          peps.Contents,
                          references.AnonymousHyperlinks,
                          references.IndirectHyperlinks,
                          peps.TargetNotes,
                          references.Footnotes,
                          references.ExternalTargets,
                          references.InternalTargets,)

    settings_default_overrides = {'pep_references': 1, 'rfc_references': 1}

    inliner_class = rst.states.Inliner

    def __init__(self, parser=None, parser_name=None):
        """`parser` should be ``None``."""
        if parser is None:
            parser = rst.Parser(rfc2822=1, inliner=self.inliner_class())
        standalone.Reader.__init__(self, parser, '')
