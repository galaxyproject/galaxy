from __future__ import absolute_import

import logging

import mako.exceptions


log = logging.getLogger(__name__)


def build_template_error_formatters():
    """
    Build a list of template error formatters for WebError. When an error
    occurs, WebError pass the exception to each function in this list until
    one returns a value, which will be displayed on the error page.
    """
    formatters = []
    # Formatter for mako

    def mako_html_data( exc_value ):
        if isinstance( exc_value, ( mako.exceptions.CompileException, mako.exceptions.SyntaxException ) ):
            return mako.exceptions.html_error_template().render( full=False, css=False )
        if isinstance( exc_value, AttributeError ) and exc_value.args[0].startswith( "'Undefined' object has no attribute" ):
            return mako.exceptions.html_error_template().render( full=False, css=False )
    formatters.append( mako_html_data )
    return formatters


def wrap_if_allowed(app, stack, wrap, name=None, args=None, kwargs=None,
                    alt_wrap=None, alt_name=None, alt_args=None, alt_kwargs=None):
    """
    Wrap the application with the given method if the application stack allows for it.

    :type   app:    :class:`galaxy.web.framework.webapp.WebApplication` subclass
    :param  app:    application to wrap
    :type   stack:  :class:`galaxy.web.stack.ApplicationStack` subclass
    :param  stack:  instance of application stack implementing `allowed_middleware()` method
    :type   wrap:   types.FunctionType or types.LambdaType
    :param  wrap:   function to wrap application with
    :type   name:   str
    :param  name:   alternative wrap function name for logging purposes (`wrap.__name__` if None)
    :type   args:   list
    :param  args:   arguments to pass to `wrap` (not including `app` itself)
    :type   kwargs: dict
    :param  kwargs: keyword arguments to pass to `wrap`
    """
    name = name or wrap.__name__
    if stack.allowed_middleware(wrap):
        args = args or []
        kwargs = kwargs or {}
        log.debug("Enabling '%s' middleware", name)
        return wrap(app, *args, **kwargs)
    else:
        log.warning("'%s' is enabled in your configuration but the %s application stack does not support it, this "
                    "middleware has been disabled", name, stack.name)
        if alt_wrap:
            app = wrap_if_allowed(app, stack, alt_wrap, name=alt_name, args=alt_args, kwargs=alt_kwargs)
        return app
