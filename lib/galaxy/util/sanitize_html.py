"""
HTML Sanitizer (lists of acceptable_* and _BaseHTMLProcessor ripped from feedparser)
TODO: remove BaseHTMLProcessor (only used one time for Page processing)
"""
import re
import sgmllib

import bleach
from six import unichr
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
    unichr(128): unichr(8364),  # euro sign
    unichr(130): unichr(8218),  # single low-9 quotation mark
    unichr(131): unichr(402),  # latin small letter f with hook
    unichr(132): unichr(8222),  # double low-9 quotation mark
    unichr(133): unichr(8230),  # horizontal ellipsis
    unichr(134): unichr(8224),  # dagger
    unichr(135): unichr(8225),  # double dagger
    unichr(136): unichr(710),  # modifier letter circumflex accent
    unichr(137): unichr(8240),  # per mille sign
    unichr(138): unichr(352),  # latin capital letter s with caron
    unichr(139): unichr(8249),  # single left-pointing angle quotation mark
    unichr(140): unichr(338),  # latin capital ligature oe
    unichr(142): unichr(381),  # latin capital letter z with caron
    unichr(145): unichr(8216),  # left single quotation mark
    unichr(146): unichr(8217),  # right single quotation mark
    unichr(147): unichr(8220),  # left double quotation mark
    unichr(148): unichr(8221),  # right double quotation mark
    unichr(149): unichr(8226),  # bullet
    unichr(150): unichr(8211),  # en dash
    unichr(151): unichr(8212),  # em dash
    unichr(152): unichr(732),  # small tilde
    unichr(153): unichr(8482),  # trade mark sign
    unichr(154): unichr(353),  # latin small letter s with caron
    unichr(155): unichr(8250),  # single right-pointing angle quotation mark
    unichr(156): unichr(339),  # latin small ligature oe
    unichr(158): unichr(382),  # latin small letter z with caron
    unichr(159): unichr(376)}  # latin capital letter y with diaeresis


class _BaseHTMLProcessor(sgmllib.SGMLParser):
    bare_ampersand = re.compile("&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)")
    elements_no_end_tag = ['area', 'base', 'basefont', 'br', 'col', 'frame', 'hr',
                           'img', 'input', 'isindex', 'link', 'meta', 'param']

    def __init__(self, encoding, type):
        self.encoding = encoding
        self.type = type
        # if _debug: sys.stderr.write('entering BaseHTMLProcessor, encoding=%s\n' % self.encoding)
        sgmllib.SGMLParser.__init__(self)

    def reset(self):
        self.pieces = []
        sgmllib.SGMLParser.reset(self)

    def _shorttag_replace(self, match):
        tag = match.group(1)
        if tag in self.elements_no_end_tag:
            return '<' + tag + ' />'
        else:
            return '<' + tag + '></' + tag + '>'

    def parse_starttag(self, i):
        j = sgmllib.SGMLParser.parse_starttag(self, i)
        if self.type == 'application/xhtml+xml':
            if j > 2 and self.rawdata[j - 2:j] == '/>':
                self.unknown_endtag(self.lasttag)
        return j

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
            strattrs = ''.join([' %s="%s"' % (k, v) for k, v in uattrs])
        if tag in self.elements_no_end_tag:
            self.pieces.append('<%s%s />' % (tag, strattrs))
        else:
            self.pieces.append('<%s%s>' % (tag, strattrs))

    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be 'pre'
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%(tag)s>" % locals())

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        # Reconstruct the original character reference.
        if ref.startswith('x'):
            value = unichr(int(ref[1:], 16))
        else:
            value = unichr(int(ref))

        if value in _cp1252.keys():
            self.pieces.append('&#%s;' % hex(ord(_cp1252[value]))[1:])
        else:
            self.pieces.append('&#%(ref)s;' % locals())

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        if ref in name2codepoint:
            self.pieces.append('&%(ref)s;' % locals())
        else:
            self.pieces.append('&amp;%(ref)s' % locals())

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        self.pieces.append(text)

    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append('<!--%(text)s-->' % locals())

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append('<?%(text)s>' % locals())

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append('<!%(text)s>' % locals())

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
