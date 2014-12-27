from markupsafe import escape as raw_escape

ALLOWED_ELEMENTS = ["<b>", "</b>", "<br/>"]
ALLOWED_MAP = dict(map(lambda x: (x, raw_escape(x)), ALLOWED_ELEMENTS))


def escape( value ):
    """ A tool shed variant of markupsafe.escape that allows a select few
    HTML elements that are repeatedly used in messages created deep
    in the toolshed components. Ideally abstract things would be produced
    in these components and messages in the views or client side - this is
    what should be worked toward - but for now - we have this hack.

    >>> escape("A <b>repo</b>")
    u'A <b>repo</b>'
    """
    escaped = str( raw_escape( value ) )
    # Unescape few selected tags.
    for key, value in ALLOWED_MAP.iteritems():
        escaped = escaped.replace(value, key)
    return escaped
