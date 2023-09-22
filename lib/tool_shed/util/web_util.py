from markupsafe import escape as raw_escape

ALLOWED_ELEMENTS = ["<b>", "</b>", "<br/>"]
ALLOWED_MAP = {x: raw_escape(x) for x in ALLOWED_ELEMENTS}


def escape(string):
    """A tool shed variant of markupsafe.escape that allows a select few
    HTML elements that are repeatedly used in messages created deep
    in the toolshed components. Ideally abstract things would be produced
    in these components and messages in the views or client side - this is
    what should be worked toward - but for now - we have this hack.

    >>> assert escape(u"A <b>cómplǐcḁtëd strĩñg</b>") == u'A <b>cómplǐcḁtëd strĩñg</b>'
    """
    escaped = str(raw_escape(string))
    # Unescape few selected tags.
    for key, value in ALLOWED_MAP.items():
        escaped = escaped.replace(value, key)
    return escaped
