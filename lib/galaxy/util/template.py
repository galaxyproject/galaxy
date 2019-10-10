"""Entry point for the usage of Cheetah templating within Galaxy."""
from Cheetah.Template import Template

from . import unicodify


def fill_template(template_text, context=None, **kwargs):
    """Fill a cheetah template out for specified context.

    If template_text is None, an exception will be thrown, if context
    is None (the default) - keyword arguments to this function will be used
    as the context.
    """
    if template_text is None:
        raise TypeError("Template text specified as None to fill_template.")
    if not context:
        context = kwargs
    return unicodify(Template(source=template_text, searchList=[context]))
