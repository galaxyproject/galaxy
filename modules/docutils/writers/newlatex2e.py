"""
:Author: Felix Wiemann
:Contact: Felix_Wiemann@ososo.de
:Revision: $Revision: 3376 $
:Date: $Date: 2005-05-26 23:33:24 +0200 (Thu, 26 May 2005) $
:Copyright: This module has been placed in the public domain.

LaTeX2e document tree Writer.
"""

# Thanks to Engelbert Gruber and various contributors for the original
# LaTeX writer, some code and many ideas of which have been used for
# this writer.

__docformat__ = 'reStructuredText'


from __future__ import nested_scopes

import re
import os.path
from types import ListType

import docutils
from docutils import nodes, writers, utils


class Writer(writers.Writer):

    supported = ('newlatex', 'newlatex2e')
    """Formats this writer supports."""

    settings_spec = (
        'LaTeX-Specific Options',
        'The LaTeX "--output-encoding" default is "latin-1:strict". '
        'Note that this LaTeX writer is still EXPERIMENTAL.',
        (('Specify a stylesheet file.  The path is used verbatim to include '
          'the file.  Overrides --stylesheet-path.',
          ['--stylesheet'],
          {'default': '', 'metavar': '<file>',
           'overrides': 'stylesheet_path'}),
         ('Specify a stylesheet file, relative to the current working '
          'directory.  Overrides --stylesheet.',
          ['--stylesheet-path'],
          {'metavar': '<file>', 'overrides': 'stylesheet'}),
         ('Specify a uesr stylesheet file.  See --stylesheet.',
          ['--user-stylesheet'],
          {'default': '', 'metavar': '<file>',
           'overrides': 'user_stylesheet_path'}),
         ('Specify a user stylesheet file.  See --stylesheet-path.',
          ['--user-stylesheet-path'],
          {'metavar': '<file>', 'overrides': 'user_stylesheet'})
         ),)

    settings_defaults = {'output_encoding': 'latin-1',
                         'trim_footnote_reference_space': 1,
                         # Currently unsupported:
                         'docinfo_xform': 0,
                         # During development:
                         'traceback': 1}

    relative_path_settings = ('stylesheet_path',)

    config_section = 'newlatex2e writer'
    config_section_dependencies = ('writers',)

    output = None
    """Final translated form of `document`."""

    def __init__(self):
        writers.Writer.__init__(self)
        self.translator_class = LaTeXTranslator

    def translate(self):
        visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        assert not visitor.context, 'context not empty: %s' % visitor.context
        self.output = visitor.astext()
        self.head = visitor.header
        self.body = visitor.body


class Babel:
    """Language specifics for LaTeX."""
    # country code by a.schlock.
    # partly manually converted from iso and babel stuff, dialects and some
    _ISO639_TO_BABEL = {
        'no': 'norsk',     # added by hand ( forget about nynorsk?)
        'gd': 'scottish',  # added by hand
        'hu': 'magyar',    # added by hand
        'pt': 'portuguese',# added by hand
        'sl': 'slovenian',
        'af': 'afrikaans',
        'bg': 'bulgarian',
        'br': 'breton',
        'ca': 'catalan',
        'cs': 'czech',
        'cy': 'welsh',
        'da': 'danish',
        'fr': 'french',
        # french, francais, canadien, acadian
        'de': 'ngerman',  # rather than german
        # ngerman, naustrian, german, germanb, austrian
        'el': 'greek',
        'en': 'english',
        # english, USenglish, american, UKenglish, british, canadian
        'eo': 'esperanto',
        'es': 'spanish',
        'et': 'estonian',
        'eu': 'basque',
        'fi': 'finnish',
        'ga': 'irish',
        'gl': 'galician',
        'he': 'hebrew',
        'hr': 'croatian',
        'hu': 'hungarian',
        'is': 'icelandic',
        'it': 'italian',
        'la': 'latin',
        'nl': 'dutch',
        'pl': 'polish',
        'pt': 'portuguese',
        'ro': 'romanian',
        'ru': 'russian',
        'sk': 'slovak',
        'sr': 'serbian',
        'sv': 'swedish',
        'tr': 'turkish',
        'uk': 'ukrainian'
    }

    def __init__(self, lang):
        self.language = lang

    def get_language(self):
        if self._ISO639_TO_BABEL.has_key(self.language):
            return self._ISO639_TO_BABEL[self.language]
        else:
            # Support dialects.
            l = self.language.split("_")[0]
            if self._ISO639_TO_BABEL.has_key(l):
                return self._ISO639_TO_BABEL[l]
        return None


class LaTeXException(Exception):
    """
    Exception base class to for exceptions which influence the
    automatic generation of LaTeX code.
    """


class SkipAttrParentLaTeX(LaTeXException):
    """
    Do not generate \Dattr and \renewcommand{\Dparent}{...} for this
    node.

    To be raised from before_... methods.
    """


class SkipParentLaTeX(LaTeXException):
    """
    Do not generate \renewcommand{\DNparent}{...} for this node.

    To be raised from before_... methods.
    """


class LaTeXTranslator(nodes.SparseNodeVisitor):

    # Start with left double quote.
    left_quote = 1

    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)
        self.settings = document.settings
        self.header = []
        self.body = []
        self.context = []
        self.stylesheet_path = utils.get_stylesheet_reference(
            self.settings, os.path.join(os.getcwd(), 'dummy'))
        if self.stylesheet_path:
            self.settings.record_dependencies.add(self.stylesheet_path)
        # This ugly hack will be cleaned up when refactoring the
        # stylesheet mess.
        self.settings.stylesheet = self.settings.user_stylesheet
        self.settings.stylesheet_path = self.settings.user_stylesheet_path
        self.user_stylesheet_path = utils.get_stylesheet_reference(
            self.settings, os.path.join(os.getcwd(), 'dummy'))
        if self.user_stylesheet_path:
            self.settings.record_dependencies.add(self.user_stylesheet_path)
        self.write_header()
        for key, value in self.character_map.items():
            self.character_map[key] = '{%s}' % value

    def write_header(self):
        a = self.header.append
        a('%% Generated by Docutils %s <http://docutils.sourceforge.net>.\n'
          % docutils.__version__)
        if self.user_stylesheet_path:
            a('% User stylesheet:')
            a(r'\input{%s}' % self.user_stylesheet_path)
        a('% Docutils stylesheet:')
        a(r'\input{%s}' % self.stylesheet_path)
        a('')
        a('% Definitions for Docutils Nodes:')
        for node_name in nodes.node_class_names:
            a(r'\providecommand{\DN%s}[1]{#1}' % node_name.replace('_', ''))
        a('')
        a('% Auxiliary definitions:')
        a(r'\providecommand{\Dsetattr}[2]{}')
        a(r'\providecommand{\Dparent}{} % variable')
        a(r'\providecommand{\Dattr}[5]{#5}')
        a(r'\providecommand{\Dattrlen}{} % variable')
        a(r'\providecommand{\Dtitleastext}{x}')
        a(r'\providecommand{\Dsinglebackref}{} % variable')
        a(r'\providecommand{\Dmultiplebackrefs}{} % variable')
        a('\n\n')

    def to_latex_encoding(self,docutils_encoding):
        """
        Translate docutils encoding name into latex's.

        Default fallback method is remove "-" and "_" chars from
        docutils_encoding.
        """
        tr = {  "iso-8859-1": "latin1",     # west european
                "iso-8859-2": "latin2",     # east european
                "iso-8859-3": "latin3",     # esperanto, maltese
                "iso-8859-4": "latin4",     # north european,scandinavian, baltic
                "iso-8859-5": "iso88595",   # cyrillic (ISO)
                "iso-8859-9": "latin5",     # turkish
                "iso-8859-15": "latin9",    # latin9, update to latin1.
                "mac_cyrillic": "maccyr",   # cyrillic (on Mac)
                "windows-1251": "cp1251",   # cyrillic (on Windows)
                "koi8-r": "koi8-r",         # cyrillic (Russian)
                "koi8-u": "koi8-u",         # cyrillic (Ukrainian)
                "windows-1250": "cp1250",   #
                "windows-1252": "cp1252",   #
                "us-ascii": "ascii",        # ASCII (US)
                # unmatched encodings
                #"": "applemac",
                #"": "ansinew",  # windows 3.1 ansi
                #"": "ascii",    # ASCII encoding for the range 32--127.
                #"": "cp437",    # dos latine us
                #"": "cp850",    # dos latin 1
                #"": "cp852",    # dos latin 2
                #"": "decmulti",
                #"": "latin10",
                #"iso-8859-6": ""   # arabic
                #"iso-8859-7": ""   # greek
                #"iso-8859-8": ""   # hebrew
                #"iso-8859-10": ""   # latin6, more complete iso-8859-4
             }
        if tr.has_key(docutils_encoding.lower()):
            return tr[docutils_encoding.lower()]
        return docutils_encoding.translate(string.maketrans("",""),"_-").lower()

    def language_label(self, docutil_label):
        return self.language.labels[docutil_label]

    # To do: Use unimap.py from TeXML instead.  Have to deal with
    # legal cruft before, because it's LPGL.
    character_map_string = r"""
        \ \textbackslash
        { \{
        } \}
        $ \$
        & \&
        % \%
        # \#
        [ [
        ] ]
        - -
        ` `
        ' '
        , ,
        " "
        | \textbar
        < \textless
        > \textgreater
        ^ \textasciicircum
        ~ \textasciitilde
        _ \Dtextunderscore
        """

    #special_map = {'\n': ' ', '\r': ' ', '\t': ' ', '\v': ' ', '\f': ' '}

    unicode_map = {
        u'\u00A0': '~',
        u'\u2009': '{\\,}',
        u'\u2013': '{--}',
        u'\u2014': '{---}',
        u'\u2018': '`',
        u'\u2019': '\'',
        u'\u201A': ',',
        u'\u201C': '``',
        u'\u201D': "''",
        u'\u201E': ',,',
        u'\u2020': '{\\dag}',
        u'\u2021': '{\\ddag}',
        u'\u2026': '{\\dots}',
        u'\u2122': '{\\texttrademark}',
        u'\u21d4': '{$\\Leftrightarrow$}',
        }

    character_map = {}
    for pair in character_map_string.strip().split('\n'):
        char, replacement = pair.split()
        character_map[char] = replacement
    character_map.update(unicode_map)
    #character_map.update(special_map)

    def encode(self, text, attval=0):
        """
        Encode special characters in ``text`` and return it.

        If attval is true, preserve as much as possible verbatim (used in
        attribute value encoding).
        """
        if not attval:
            get = self.character_map.get
        else:
            # According to
            # <http://www-h.eng.cam.ac.uk/help/tpl/textprocessing/teTeX/latex/latex2e-html/ltx-164.html>,
            # the following characters are special: # $ % & ~ _ ^ \ { }
            # These work without special treatment in macro parameters:
            # $, &, ~, _, ^
            get = {'#': '\\#',
                   '%': '\\%',
                   # We cannot do anything about backslashes.
                   '\\': '',
                   '{': '\\{',
                   '}': '\\}',
                   # The quotation mark may be redefined by babel.
                   '"': '"{}',
                   }.get
        text = ''.join([get(c, c) for c in text])
        if (self.literal_block or self.inline_literal) and not attval:
            # NB: We can have inline literals within literal blocks.
            # Shrink '\r\n'.
            text = text.replace('\r\n', '\n')
            # Convert space.  If "{ }~~~~~" is wrapped (at the
            # brace-enclosed space "{ }"), the following non-breaking
            # spaces ("~~~~") do *not* wind up at the beginning of the
            # next line.  Also note that, for some not-so-obvious
            # reason, no hyphenation is done if the breaking space ("{
            # }") comes *after* the non-breaking spaces.
            if self.literal_block:
                # Replace newlines with real newlines.
                text = text.replace('\n', '\mbox{}\\\\')
                firstspace = '~'
            else:
                firstspace = '{ }'
            text = re.sub(r'\s+', lambda m: firstspace +
                          '~' * (len(m.group()) - 1), text)
            # Protect hyphens; if we don't, line breaks will be
            # possible at the hyphens and even the \textnhtt macro
            # from the hyphenat package won't change that.
            text = text.replace('-', r'\mbox{-}')
            text = text.replace("'", r'{\Dtextliteralsinglequote}')
            return text
        else:
            if not attval:
                # Replace space with single protected space.
                text = re.sub(r'\s+', '{ }', text)
                # Replace double quotes with macro calls.
                L = []
                for part in text.split('"'):
                    if L:
                        # Insert quote.
                        L.append(self.left_quote and r'\Dtextleftdblquote' or
                                 r'\Dtextrightdblquote')
                        self.left_quote = not self.left_quote
                    L.append(part)
                return ''.join(L)
            else:
                return text

    def astext(self):
        return '\n'.join(self.header) + (''.join(self.body))

    def append(self, text, newline='%\n'):
        """
        Append text, stripping newlines, producing nice LaTeX code.
        """
        lines = ['  ' * self.indentation_level + line + newline
                 for line in text.splitlines(0)]
        self.body.append(''.join(lines))

    def visit_Text(self, node):
        self.append(self.encode(node.astext()))

    def depart_Text(self, node):
        pass

    def before_title(self, node):
        self.append(r'\renewcommand{\Dtitleastext}{%s}'
                    % self.encode(node.astext()))
        self.append(r'\renewcommand{\Dhassubtitle}{%s}'
                    % ((len(node.parent) > 2 and
                        isinstance(node.parent[1], nodes.subtitle))
                       and 'true' or 'false'))

    literal_block = 0

    def visit_literal_block(self, node):
        self.literal_block = 1

    def depart_literal_block(self, node):
        self.literal_block = 0

    visit_doctest_block = visit_literal_block
    depart_doctest_block = depart_literal_block

    inline_literal = 0

    def visit_literal(self, node):
        self.inline_literal += 1

    def depart_literal(self, node):
        self.inline_literal -= 1

    def visit_comment(self, node):
        self.append('\n'.join(['% ' + line for line
                               in node.astext().splitlines(0)]), newline='\n')
        raise nodes.SkipChildren

    bullet_list_level = 0

    def visit_bullet_list(self, node):
        self.append(r'\Dsetbullet{\labelitem%s}' %
                    ['i', 'ii', 'iii', 'iv'][min(self.bullet_list_level, 3)])
        self.bullet_list_level += 1

    def depart_bullet_list(self, node):
        self.bullet_list_level -= 1

    enum_styles = {'arabic': 'arabic', 'loweralpha': 'alph', 'upperalpha':
                   'Alph', 'lowerroman': 'roman', 'upperroman': 'Roman'}

    enum_counter = 0

    def visit_enumerated_list(self, node):
        # We create our own enumeration list environment.  This allows
        # to set the style and starting value and unlimited nesting.
        # Maybe this can be moved to the stylesheet?
        self.enum_counter += 1
        enum_prefix = self.encode(node['prefix'])
        enum_suffix = self.encode(node['suffix'])
        enum_type = '\\' + self.enum_styles.get(node['enumtype'], r'arabic')
        start = node.get('start', 1) - 1
        counter = 'Denumcounter%d' % self.enum_counter
        self.append(r'\Dmakeenumeratedlist{%s}{%s}{%s}{%s}{%s}{'
                    % (enum_prefix, enum_type, enum_suffix, counter, start))
                    # for Emacs: }

    def depart_enumerated_list(self, node):
        self.append('}')  # for Emacs: {

    def before_list_item(self, node):
        # XXX needs cleanup.
        if (len(node) and (isinstance(node[-1], nodes.TextElement) or
                           isinstance(node[-1], nodes.Text)) and
            node.parent.index(node) == len(node.parent) - 1):
            node['lastitem'] = 'true'

    before_line = before_list_item

    def before_raw(self, node):
        if 'latex' in node.get('format', '').split():
            # We're inserting the text in before_raw and thus outside
            # of \DN... and \Dattr in order to make grouping with
            # curly brackets work.
            self.append(node.astext())
        raise nodes.SkipChildren

    def process_backlinks(self, node, type):
        self.append(r'\renewcommand{\Dsinglebackref}{}')
        self.append(r'\renewcommand{\Dmultiplebackrefs}{}')
        if len(node['backrefs']) > 1:
            refs = []
            for i in range(len(node['backrefs'])):
                refs.append(r'\Dmulti%sbacklink{%s}{%s}'
                            % (type, node['backrefs'][i], i + 1))
            self.append(r'\renewcommand{\Dmultiplebackrefs}{(%s){ }}'
                        % ', '.join(refs))
        elif len(node['backrefs']) == 1:
            self.append(r'\renewcommand{\Dsinglebackref}{%s}'
                        % node['backrefs'][0])

    def visit_footnote(self, node):
        self.process_backlinks(node, 'footnote')

    def visit_citation(self, node):
        self.process_backlinks(node, 'citation')

    def before_table(self, node):
        # A tables contains exactly one tgroup.  See before_tgroup.
        pass

    def before_tgroup(self, node):
        widths = []
        total_width = 0
        for i in range(int(node['cols'])):
            assert isinstance(node[i], nodes.colspec)
            widths.append(int(node[i]['colwidth']) + 1)
            total_width += widths[-1]
        del node[:len(widths)]
        tablespec = '|'
        for w in widths:
            # 0.93 is probably wrong in many cases.  XXX Find a
            # solution which works *always*.
            tablespec += r'p{%s\linewidth}|' % (0.93 * w /
                                                max(total_width, 60))
        self.append(r'\Dmaketable{%s}{' % tablespec)
        self.context.append('}')
        raise SkipAttrParentLaTeX

    def depart_tgroup(self, node):
        self.append(self.context.pop())

    def before_row(self, node):
        raise SkipAttrParentLaTeX

    def before_thead(self, node):
        raise SkipAttrParentLaTeX

    def before_tbody(self, node):
        raise SkipAttrParentLaTeX

    def is_simply_entry(self, node):
        return (len(node) == 1 and isinstance(node[0], nodes.paragraph) or
                len(node) == 0)

    def before_entry(self, node):
        is_leftmost = 0
        if node.hasattr('morerows'):
            self.document.reporter.severe('Rowspans are not supported.')
            # Todo: Add empty cells below rowspanning cell and issue
            # warning instead of severe.
        if node.hasattr('morecols'):
            # The author got a headache trying to implement
            # multicolumn support.
            if not self.is_simply_entry(node):
                self.document.reporter.severe(
                    'Colspanning table cells may only contain one paragraph.')
                # Todo: Same as above.
            # The number of columns this entry spans (as a string).
            colspan = int(node['morecols']) + 1
            del node['morecols']
        else:
            colspan = 1
        # Macro to call.
        macro_name = r'\Dcolspan'
        if node.parent.index(node) == 0:
            # Leftmost column.
            macro_name += 'left'
            is_leftmost = 1
        if colspan > 1:
            self.append('%s{%s}{' % (macro_name, colspan))
            self.context.append('}')
        else:
            # Do not add a multicolumn with colspan 1 beacuse we need
            # at least one non-multicolumn cell per column to get the
            # desired column widths, and we can only do colspans with
            # cells consisting of only one paragraph.
            if not is_leftmost:
                self.append(r'\Dsubsequententry{')
                self.context.append('}')
            else:
                self.context.append('')
        if isinstance(node.parent.parent, nodes.thead):
            node['tableheaderentry'] = 'true'

        # Don't add \renewcommand{\Dparent}{...} because there must
        # not be any non-expandable commands in front of \multicolumn.
        raise SkipParentLaTeX

    def depart_entry(self, node):
        self.append(self.context.pop())

    def before_substitution_definition(self, node):
        raise nodes.SkipNode

    indentation_level = 0

    def node_name(self, node):
        return node.__class__.__name__.replace('_', '')

    def propagate_attributes(self, node):
        # Propagate attributes using \Dattr macros.
        node_name = self.node_name(node)
        attlist = []
        if isinstance(node, nodes.Element):
            attlist = node.attlist()
        numatts = 0
        pass_contents = self.pass_contents(node)
        for key, value in attlist:
            if isinstance(value, ListType):
                self.append(r'\renewcommand{\Dattrlen}{%s}' % len(value))
                for i in range(len(value)):
                    self.append(r'\Dattr{%s}{%s}{%s}{%s}{' %
                                (i+1, key, self.encode(value[i], attval=1),
                                 node_name))
                    if not pass_contents:
                        self.append('}')
                numatts += len(value)
            else:
                self.append(r'\Dattr{}{%s}{%s}{%s}{' %
                            (key, self.encode(unicode(value), attval=1),
                             node_name))
                if not pass_contents:
                    self.append('}')
                numatts += 1
        if pass_contents:
            self.context.append('}' * numatts)  # for Emacs: {
        else:
            self.context.append('')

    def visit_docinfo(self, node):
        raise NotImplementedError('Docinfo not yet implemented.')

    def visit_document(self, node):
        document = node
        # Move IDs into TextElements.  This won't work for images.
        # Need to review this.
        for node in document.traverse(lambda n: isinstance(n, nodes.Element)):
            if node.has_key('ids') and not isinstance(node,
                                                      nodes.TextElement):
                next_text_element = node.next_node(
                    lambda n: isinstance(n, nodes.TextElement))
                if next_text_element:
                    next_text_element['ids'].extend(node['ids'])
                    node['ids'] = []

    def pass_contents(self, node):
        r"""
        Return true if the node contents should be passed in
        parameters of \DN... and \Dattr.
        """
        return not isinstance(node, (nodes.document, nodes.section))

    def dispatch_visit(self, node):
        skip_attr = skip_parent = 0
        # TreePruningException to be propagated.
        tree_pruning_exception = None
        if hasattr(self, 'before_' + node.__class__.__name__):
            try:
                getattr(self, 'before_' + node.__class__.__name__)(node)
            except SkipParentLaTeX:
                skip_parent = 1
            except SkipAttrParentLaTeX:
                skip_attr = 1
                skip_parent = 1
            except nodes.SkipNode:
                raise
            except (nodes.SkipChildren, nodes.SkipSiblings), instance:
                tree_pruning_exception = instance
            except nodes.SkipDeparture:
                raise NotImplementedError(
                    'SkipDeparture not usable in LaTeX writer')

        if not isinstance(node, nodes.Text):
            node_name = self.node_name(node)
            # attribute_deleters will be appended to self.context.
            attribute_deleters = []
            if not skip_parent and not isinstance(node, nodes.document):
                self.append(r'\renewcommand{\Dparent}{%s}'
                            % self.node_name(node.parent))
                for name, value in node.attlist():
                    # @@@ Evaluate if this is really needed and refactor.
                    if not isinstance(value, ListType) and not ':' in name:
                        macro = r'\DcurrentN%sA%s' % (node_name, name)
                        self.append(r'\def%s{%s}' % (
                            macro, self.encode(unicode(value), attval=1)))
                        attribute_deleters.append(r'\let%s=\relax' % macro)
            self.context.append('\n'.join(attribute_deleters))
            if self.pass_contents(node):
                self.append(r'\DN%s{' % node_name)
                self.context.append('}')
            else:
                self.append(r'\Dvisit%s' % node_name)
                self.context.append(r'\Ddepart%s' % node_name)
            self.indentation_level += 1
            if not skip_attr:
                self.propagate_attributes(node)
            else:
                self.context.append('')

        if (isinstance(node, nodes.TextElement) and
            not isinstance(node.parent, nodes.TextElement)):
            # Reset current quote to left.
            self.left_quote = 1

        # Call visit_... method.
        try:
            nodes.SparseNodeVisitor.dispatch_visit(self, node)
        except LaTeXException:
            raise NotImplementedError(
                'visit_... methods must not raise LaTeXExceptions')

        if tree_pruning_exception:
            # Propagate TreePruningException raised in before_... method.
            raise tree_pruning_exception

    def is_invisible(self, node):
        # Return true if node is invisible or moved away in the LaTeX
        # rendering.
        return (isinstance(node, nodes.Invisible) or
                isinstance(node, nodes.footnote) or
                isinstance(node, nodes.citation) or
                # We never know what's inside raw nodes, and often
                # they *are* invisible.  So let's have the user take
                # care of them.
                isinstance(node, nodes.raw) or
                # Horizontally aligned image or figure.
                node.get('align', None) in ('left', 'center', 'right'))

    def needs_space(self, node):
        # Return true if node is a visible block-level element.
        return ((isinstance(node, nodes.Body) or
                 isinstance(node, nodes.topic) or
                 #isinstance(node, nodes.rubric) or
                 isinstance(node, nodes.transition) or
                 isinstance(node, nodes.caption) or
                 isinstance(node, nodes.legend)) and
                not (self.is_invisible(node) or
                     isinstance(node.parent, nodes.TextElement)))

    def dispatch_departure(self, node):
        # Call departure method.
        nodes.SparseNodeVisitor.dispatch_departure(self, node)

        if not isinstance(node, nodes.Text):
            # Close attribute and node handler call (\DN...{...}).
            self.indentation_level -= 1
            self.append(self.context.pop() + self.context.pop())
            # Delete \Dcurrent... attribute macros.
            self.append(self.context.pop())
            # Insert space.
            if self.needs_space(node):
                # Next sibling.
                next_node = node.next_node(
                    ascend=0, siblings=1, descend=0,
                    condition=lambda n: not self.is_invisible(n))
                if self.needs_space(next_node):
                    # Insert space.
                    if isinstance(next_node, nodes.paragraph):
                        if isinstance(node, nodes.paragraph):
                            # Space between paragraphs.
                            self.append(r'\Dparagraphspace')
                        else:
                            # Space in front of a paragraph.
                            self.append(r'\Dauxiliaryparspace')
                    else:
                        # Space in front of something else than a paragraph.
                        self.append(r'\Dauxiliaryspace')
