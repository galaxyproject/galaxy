"""
Code derived from WebHelpers: https://bitbucket.org/bbangert/webhelpers

Licensed under the MIT license: https://bitbucket.org/bbangert/webhelpers/src/tip/LICENSE
"""
from __future__ import print_function

from markupsafe import escape_silent


def format_attrs(**attrs):
    """Format HTML attributes into a string of ' key="value"' pairs which
    can be inserted into an HTML tag.

    The attributes are sorted alphabetically.  If any value is None, the entire
    attribute is suppressed.

    Usage:
    >>> format_attrs(p=2, q=3) == u' p="2" q="3"'
    True
    >>> format_attrs(p=2, q=None) == u' p="2"'
    True
    >>> format_attrs(p=None) == u''
    True
    """
    strings = [u' %s="%s"' % (attr, escape_silent(value))
        for attr, value in sorted(attrs.items())
        if value is not None]
    return u''.join(strings)


def javascript_link(*urls, **attrs):
    """Return script include tags for the specified javascript URLs.

    ``urls`` should be the exact URLs desired.  A previous version of this
    helper added magic prefixes; this is no longer the case.

    Specify the keyword argument ``defer=True`` to enable the script
    defer attribute.

    Examples::

        >>> print(javascript_link('/javascripts/prototype.js', '/other-javascripts/util.js'))
        <script src="/javascripts/prototype.js" type="text/javascript"></script>
        <script src="/other-javascripts/util.js" type="text/javascript"></script>

        >>> print(javascript_link('/app.js', '/test/test.1.js'))
        <script src="/app.js" type="text/javascript"></script>
        <script src="/test/test.1.js" type="text/javascript"></script>
    """
    if 'defer' in attrs:
        if attrs['defer']:
            attrs['defer'] = 'defer'
        else:
            del attrs['defer']
    attrs['type'] = 'text/javascript'
    tag_template = u'<script%s></script>'
    tags = []
    for url in urls:
        attrs['src'] = url
        tag = tag_template % format_attrs(**attrs)
        tags.append(tag)
    return u"\n".join(tags)


def stylesheet_link(*urls, **attrs):
    """Return CSS link tags for the specified stylesheet URLs.

    ``urls`` should be the exact URLs desired.  A previous version of this
    helper added magic prefixes; this is no longer the case.

    Examples::

        >>> print(stylesheet_link('/stylesheets/style.css'))
        <link href="/stylesheets/style.css" media="screen" rel="stylesheet" type="text/css" />

        >>> print(stylesheet_link('/stylesheets/dir/file.css', media='all'))
        <link href="/stylesheets/dir/file.css" media="all" rel="stylesheet" type="text/css" />
    """
    if "href" in attrs:
        raise TypeError("keyword arg 'href' not allowed")
    attrs.setdefault("rel", "stylesheet")
    attrs.setdefault("type", "text/css")
    attrs.setdefault("media", "screen")
    tag_template = u'<link%s />'
    tags = []
    for url in urls:
        attrs['href'] = url
        tag = tag_template % format_attrs(**attrs)
        tags.append(tag)
    return u"\n".join(tags)
