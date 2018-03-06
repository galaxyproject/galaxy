"""
HTML Sanitizer (lists of acceptable_* and _BaseHTMLProcessor ripped from feedparser)
TODO: remove BaseHTMLProcessor (only used one time for Page processing)
"""
import re
import sgmllib

import bleach
from six.moves.html_entities import name2codepoint

_acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'article',
        'aside', 'audio', 'b', 'big', 'blockquote', 'br', 'button', 'canvas',
        'caption', 'center', 'cite', 'code', 'col', 'colgroup', 'command',
        'datagrid', 'datalist', 'dd', 'del', 'details', 'dfn', 'dialog', 'dir',
        'div', 'dl', 'dt', 'em', 'event-source', 'fieldset', 'figure',
        'footer', 'font', 'form', 'header', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'hr', 'i', 'img', 'input', 'ins', 'keygen', 'kbd', 'label', 'legend',
        'li', 'm', 'map', 'menu', 'meter', 'multicol', 'nav', 'nextid', 'ol',
        'output', 'optgroup', 'option', 'p', 'pre', 'progress', 'q', 's',
        'samp', 'section', 'select', 'small', 'sound', 'source', 'spacer',
        'span', 'strike', 'strong', 'sub', 'sup', 'table', 'tbody', 'td',
        'textarea', 'time', 'tfoot', 'th', 'thead', 'tr', 'tt', 'u', 'ul',
        'var', 'video', 'noscript']

_acceptable_attributes = ['abbr', 'accept', 'accept-charset', 'accesskey',
        'action', 'align', 'alt', 'autocomplete', 'autofocus', 'axis',
        'background', 'balance', 'bgcolor', 'bgproperties', 'border',
        'bordercolor', 'bordercolordark', 'bordercolorlight', 'bottompadding',
        'cellpadding', 'cellspacing', 'ch', 'challenge', 'char', 'charoff',
        'choff', 'charset', 'checked', 'cite', 'class', 'clear', 'color',
        'cols', 'colspan', 'compact', 'contenteditable', 'controls', 'coords',
        'data', 'datafld', 'datapagesize', 'datasrc', 'datetime', 'default',
        'delay', 'dir', 'disabled', 'draggable', 'dynsrc', 'enctype', 'end',
        'face', 'for', 'form', 'frame', 'galleryimg', 'gutter', 'headers',
        'height', 'hidefocus', 'hidden', 'high', 'href', 'hreflang', 'hspace',
        'icon', 'id', 'inputmode', 'ismap', 'keytype', 'label', 'leftspacing',
        'lang', 'list', 'longdesc', 'loop', 'loopcount', 'loopend',
        'loopstart', 'low', 'lowsrc', 'max', 'maxlength', 'media', 'method',
        'min', 'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'open',
        'optimum', 'pattern', 'ping', 'point-size', 'prompt', 'pqg',
        'radiogroup', 'readonly', 'rel', 'repeat-max', 'repeat-min', 'replace',
        'required', 'rev', 'rightspacing', 'rows', 'rowspan', 'rules', 'scope',
        'selected', 'shape', 'size', 'span', 'src', 'start', 'step', 'summary',
        'suppress', 'tabindex', 'target', 'template', 'title', 'toppadding',
        'type', 'unselectable', 'usemap', 'urn', 'valign', 'value', 'variable',
        'volume', 'vspace', 'vrml', 'width', 'wrap', 'xml:lang']

_cp1252 = {
    128: u'\u20ac',  # euro sign
    130: u'\u201a',  # single low-9 quotation mark
    131: u'\u0192',  # latin small letter f with hook
    132: u'\u201e',  # double low-9 quotation mark
    133: u'\u2026',  # horizontal ellipsis
    134: u'\u2020',  # dagger
    135: u'\u2021',  # double dagger
    136: u'\u02c6',  # modifier letter circumflex accent
    137: u'\u2030',  # per mille sign
    138: u'\u0160',  # latin capital letter s with caron
    139: u'\u2039',  # single left-pointing angle quotation mark
    140: u'\u0152',  # latin capital ligature oe
    142: u'\u017d',  # latin capital letter z with caron
    145: u'\u2018',  # left single quotation mark
    146: u'\u2019',  # right single quotation mark
    147: u'\u201c',  # left double quotation mark
    148: u'\u201d',  # right double quotation mark
    149: u'\u2022',  # bullet
    150: u'\u2013',  # en dash
    151: u'\u2014',  # em dash
    152: u'\u02dc',  # small tilde
    153: u'\u2122',  # trade mark sign
    154: u'\u0161',  # latin small letter s with caron
    155: u'\u203a',  # single right-pointing angle quotation mark
    156: u'\u0153',  # latin small ligature oe
    158: u'\u017e',  # latin small letter z with caron
    159: u'\u0178',  # latin capital letter y with diaeresis
}


class _BaseHTMLProcessor(sgmllib.SGMLParser, object):
    bare_ampersand = re.compile("&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)")
    elements_no_end_tag = set([
        'area', 'base', 'basefont', 'br', 'col', 'command', 'embed', 'frame',
        'hr', 'img', 'input', 'isindex', 'keygen', 'link', 'meta', 'param',
        'source', 'track', 'wbr'
    ])

    def reset(self):
        self.pieces = []
        sgmllib.SGMLParser.reset(self)

    def _shorttag_replace(self, match):
        tag = match.group(1)
        if tag in self.elements_no_end_tag:
            return '<' + tag + ' />'
        else:
            return '<' + tag + '></' + tag + '>'

    def feed(self, data):
        data = re.compile(r'<!((?!DOCTYPE|--|\[))', re.IGNORECASE).sub(r'&lt;!\1', data)
        data = re.sub(r'<([^<>\s]+?)\s*/>', self._shorttag_replace, data)
        data = data.replace('&#39;', "'")
        data = data.replace('&#34;', '"')
        sgmllib.SGMLParser.feed(self, data)
        sgmllib.SGMLParser.close(self)

    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class='screen'>, tag='pre', attrs=[('class', 'screen')]
        uattrs = []
        strattrs = ''
        if attrs:
            for key, value in attrs:
                value = value.replace('>', '&gt;').replace('<', '&lt;').replace('"', '&quot;')
                value = self.bare_ampersand.sub("&amp;", value)
                uattrs.append((key, value))
            strattrs = ''.join(' %s="%s"' % (k, v) for k, v in uattrs)
        if tag in self.elements_no_end_tag:
            self.pieces.append('<%s%s />' % (tag, strattrs))
        else:
            self.pieces.append('<%s%s>' % (tag, strattrs))

    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be 'pre'
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%s>" % tag)

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        # Reconstruct the original character reference.
        ref = ref.lower()
        if ref.startswith('x'):
            value = int(ref[1:], 16)
        else:
            value = int(ref)

        if value in _cp1252:
            self.pieces.append('&#%s;' % hex(ord(_cp1252[value]))[1:])
        else:
            self.pieces.append('&#%s;' % ref)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        if ref in name2codepoint or ref == 'apos':
            self.pieces.append('&%s;' % ref)
        else:
            self.pieces.append('&amp;%s' % ref)

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        self.pieces.append(text)

    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append('<!--%s-->' % text)

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append('<?%s>' % text)

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append('<!%s>' % text)

    _new_declname_match = re.compile(r'[a-zA-Z][-_.a-zA-Z0-9:]*\s*').match

    def _scan_name(self, i, declstartpos):
        rawdata = self.rawdata
        n = len(rawdata)
        if i == n:
            return None, -1
        m = self._new_declname_match(rawdata, i)
        if m:
            s = m.group()
            name = s.strip()
            if (i + len(s)) == n:
                return None, -1  # end of buffer
            return name.lower(), m.end()
        else:
            self.handle_data(rawdata)
#            self.updatepos(declstartpos, i)
            return None, -1

    def convert_charref(self, name):
        return '&#%s;' % name

    def convert_entityref(self, name):
        return '&%s;' % name

    def output(self):
        '''Return processed HTML as a single string'''
        return ''.join(self.pieces)


def sanitize_html(htmlSource):
    return bleach.clean(htmlSource, tags=_acceptable_elements, attributes=_acceptable_attributes, strip=True)
