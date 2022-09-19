import logging

import mako.exceptions

from galaxy.util import unicodify

log = logging.getLogger(__name__)


class MiddlewareWrapUnsupported(Exception):
    pass


def build_template_error_formatters():
    """
    Build a list of template error formatters for WebError. When an error
    occurs, WebError pass the exception to each function in this list until
    one returns a value, which will be displayed on the error page.
    """
    formatters = []
    # Formatter for mako

    def mako_html_data(exc_value):
        if isinstance(exc_value, (mako.exceptions.CompileException, mako.exceptions.SyntaxException)):
            return mako.exceptions.html_error_template().render(full=False, css=False)
        if isinstance(exc_value, AttributeError) and exc_value.args[0].startswith(
            "'Undefined' object has no attribute"
        ):
            return mako.exceptions.html_error_template().render(full=False, css=False)

    formatters.append(mako_html_data)
    return formatters


def wrap_if_allowed_or_fail(app, stack, wrap, name=None, args=None, kwargs=None):
    """
    Wrap the application with the given method if the application stack allows for it.

    Arguments are the same as for :func:`wrap_if_allowed`.

    Raises py:class:`MiddlewareWrapUnsupported` if the stack does not allow the middleware.
    """
    name = name or wrap.__name__
    if not stack.allowed_middleware(wrap):
        raise MiddlewareWrapUnsupported(
            "'%s' is enabled in your configuration but the %s application stack does not support it, this "
            "middleware has been disabled" % (name, stack.name)
        )
    args = args or []
    kwargs = kwargs or {}
    log.debug("Enabling '%s' middleware", name)
    return wrap(app, *args, **kwargs)


def wrap_if_allowed(app, stack, wrap, name=None, args=None, kwargs=None):
    """
    Wrap the application with the given method if the application stack allows for it.

    :type   app:    :class:`galaxy.webapps.base.webapp.WebApplication` subclass
    :param  app:    application to wrap
    :type   stack:  :class:`galaxy.web_stack.ApplicationStack` subclass
    :param  stack:  instance of application stack implementing `allowed_middleware()` method
    :type   wrap:   types.FunctionType or types.LambdaType
    :param  wrap:   function to wrap application with
    :type   name:   str
    :param  name:   alternative wrap function name for logging purposes (`wrap.__name__` if None)
    :type   args:   list
    :param  args:   arguments to pass to `wrap` (not including `app` itself)
    :type   kwargs: dict
    :param  kwargs: keyword arguments to pass to `wrap`

    Returns `app` unmodified if the stack does not allow the middleware.
    """
    try:
        return wrap_if_allowed_or_fail(app, stack, wrap, name=name, args=args, kwargs=kwargs)
    except MiddlewareWrapUnsupported as exc:
        log.warning(unicodify(exc))
        return app
