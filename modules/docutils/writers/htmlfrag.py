# Author: Ollie Rutherfurd
# Contact: oliver@rutherfurd.net
# Revision: $Revision: 2884 $
# Date: $Date: 2004-12-08 20:49:05 +0100 (Wed, 08 Dec 2004) $
# Copyright: This module has been placed in the public domain.

"""
Simple .ht (HyperText Template) document tree Writer.

.ht tmeplate files are essentially normal HTML, with
an option set of RFC 2822-like headers at the top of
the file. There must be at least one blank line between
the last header and the start of the body HTML.

See http://ht2html.sf.net/ for more information on
.ht files and ht2html..
"""

__docformat__ = 'reStructuredText'

import os
from docutils import nodes
from docutils import writers
from docutils import frontend
from docutils.writers.html4css1 import HTMLTranslator, utils


class Writer(writers.Writer):

    supported = ('htmlfrag',)
    """Formats this writer supports."""

    settings_spec = (
        'HTML-Specific Options',
        None,
        (('Specify a stylesheet URL, used verbatim.  Default is '
          '"default.css".  Overrides --stylesheet-path.',
          ['--stylesheet'],
          {'default': 'default.css', 'metavar': '<URL>',
           'overrides': 'stylesheet_path'}),
         ('Specify a stylesheet file, relative to the current working '
          'directory.  The path is adjusted relative to the output HTML '
          'file.  Overrides --stylesheet.',
          ['--stylesheet-path'],
          {'metavar': '<file>', 'overrides': 'stylesheet'}),
         ('Link to the stylesheet in the output HTML file.  This is the '
          'default.',
          ['--link-stylesheet'],
          {'dest': 'embed_stylesheet', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Embed the stylesheet in the output HTML file.  The stylesheet '
          'file must be accessible during processing (--stylesheet-path is '
          'recommended).  Default: link the stylesheet, do not embed it.',
          ['--embed-stylesheet'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Specify the initial header level.  Default is 1 for "<h1>".  '
          'Does not affect document title & subtitle (see --no-doc-title).',
          ['--initial-header-level'],
          {'choices': '1 2 3 4 5 6'.split(), 'default': '3',
           'metavar': '<level>'}),
         ('Specify the maximum width (in characters) for one-column field '
          'names.  Longer field names will span an entire row of the table '
          'used to render the field list.  Default is 14 characters.  '
          'Use 0 for "no limit".',
          ['--field-name-limit'],
          {'default': 14, 'metavar': '<level>',
           'validator': frontend.validate_nonnegative_int}),
         ('Specify the maximum width (in characters) for options in option '
          'lists.  Longer options will span an entire row of the table used '
          'to render the option list.  Default is 14 characters.  '
          'Use 0 for "no limit".',
          ['--option-limit'],
          {'default': 14, 'metavar': '<level>',
           'validator': frontend.validate_nonnegative_int}),
         ('Format for footnote references: one of "superscript" or '
          '"brackets".  Default is "brackets".',
          ['--footnote-references'],
          {'choices': ['superscript', 'brackets'], 'default': 'brackets',
           'metavar': '<format>',
           'overrides': 'trim_footnote_reference_space'}),
         ('Format for block quote attributions: one of "dash" (em-dash '
          'prefix), "parentheses"/"parens", or "none".  Default is "dash".',
          ['--attribution'],
          {'choices': ['dash', 'parentheses', 'parens', 'none'],
           'default': 'dash', 'metavar': '<format>'}),
         ('Remove extra vertical whitespace between items of bullet lists '
          'and enumerated lists, when list items are "simple" (i.e., all '
          'items each contain one paragraph and/or one "simple" sublist '
          'only).  Default: enabled.',
          ['--compact-lists'],
          {'default': 1, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable compact simple bullet and enumerated lists.',
          ['--no-compact-lists'],
          {'dest': 'compact_lists', 'action': 'store_false'}),
         ('Omit the XML declaration.  Use with caution.',
          ['--no-xml-declaration'],
          {'dest': 'xml_declaration', 'default': 1, 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Scramble email addresses to confuse harvesters.  '
          'For example, "abc@example.org" will become '
          '``<a href="mailto:%61%62%63%40...">abc at example dot org</a>``.',
          ['--cloak-email-addresses'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),))


    relative_path_settings = ('stylesheet_path',)

    output = None

    def __init__(self):
        writers.Writer.__init__(self)
        self.translator_class = HTMLFragTranslator

    def translate(self):
        visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()
        self.stylesheet = visitor.stylesheet
        self.body = visitor.body


class HTMLFragTranslator(HTMLTranslator):

    def __init__(self, document):
        # I don't believe we can embed any style content
        # the header, so always link to the stylesheet.
        document.settings.embed_stylesheet = 0
        HTMLTranslator.__init__(self, document)

    def astext(self):
        # kludge! want footer, but not '</body></html>'
        body = self.body_pre_docinfo + self.docinfo + self.body + \
                self.body_suffix[:-1]
        return ''.join(body)

# :indentSize=4:lineSeparator=\n:noTabs=true:tabSize=4:
