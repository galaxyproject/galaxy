import locale
from string import Template

DEFAULT_LOCALE_FORMAT = '%a %b %e %H:%M:%S %Y'
ISO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def expand_pretty_datetime_format(value):
    """

    >>> expand_pretty_datetime_format("%H:%M:%S %Z")
    '%H:%M:%S %Z'
    >>> locale_format = expand_pretty_datetime_format("$locale (UTC)")
    >>> import locale
    >>> expected_format = '%s (UTC)' % locale.nl_langinfo(locale.D_T_FMT)
    >>> locale_format == expected_format
    True
    >>> expand_pretty_datetime_format("$iso8601")
    '%Y-%m-%d %H:%M:%S'
    """
    locale_format = None
    try:
        locale_format = locale.nl_langinfo(locale.D_T_FMT)
    except AttributeError:  # nl_langinfo not available
        pass
    if not locale_format:
        locale_format = DEFAULT_LOCALE_FORMAT
    stock_formats = dict(
        locale=locale_format,
        iso8601=ISO_DATETIME_FORMAT,
    )
    return Template(value).safe_substitute(**stock_formats)
