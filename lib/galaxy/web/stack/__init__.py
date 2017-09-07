"""Web application stack operations
"""
from __future__ import print_function

import inspect
import logging
import os

# The uwsgi module is automatically injected by the parent uwsgi
# process and only exists that way.  If anything works, this is a
# uwsgi-managed process.
try:
    import uwsgi
except ImportError:
    uwsgi = None

try:
    from uwsgidecorators import postfork as uwsgi_postfork
except:
    uwsgi_postfork = lambda x: x    # noqa: E731
    if uwsgi is not None and hasattr(uwsgi, 'numproc'):
        print("WARNING: This is a uwsgi process but the uwsgidecorators library"
              " is unavailable.  This is likely due to using an external (not"
              " in Galaxy's virtualenv) uwsgi and you may experience errors. "
              "HINT:\n  {venv}/bin/pip install uwsgidecorators".format(
                  venv=os.environ.get('VIRTUAL_ENV', '/path/to/venv')))


log = logging.getLogger(__name__)


class ApplicationStack(object):
    name = None
    prohibited_middleware = frozenset()

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        f(*args, **kwargs)

    def workers(self):
        return []

    def allowed_middleware(self, middleware):
        if hasattr(middleware, '__name__'):
            middleware = middleware.__name__
        return middleware not in self.prohibited_middleware

    def set_postfork_server_name(self, app):
        pass


class UWSGIApplicationStack(ApplicationStack):
    name = 'uWSGI'
    prohibited_middleware = frozenset([
        'wrap_in_static',
        'EvalException',
    ])

    postfork_functions = []

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        cls.postfork_functions.append((f, args, kwargs))

    def workers(self):
        return uwsgi.workers()

    def set_postfork_server_name(self, app):
        app.config.server_name += ".%d" % uwsgi.worker_id()


class PasteApplicationStack(ApplicationStack):
    name = 'Python Paste'


class WeblessApplicationStack(ApplicationStack):
    name = 'Webless'


def application_stack_class():
    """Returns the correct ApplicationStack class for the stack under which
    this Galaxy process is running.
    """
    if uwsgi is not None and hasattr(uwsgi, 'numproc'):
        return UWSGIApplicationStack
    else:
        # cleverer ideas welcome
        for frame in inspect.stack():
            if frame[1].endswith(os.path.join('pastescript', 'loadwsgi.py')):
                return PasteApplicationStack
    return WeblessApplicationStack


def application_stack_instance():
    stack_class = application_stack_class()
    return stack_class()


def register_postfork_function(f, *args, **kwargs):
    application_stack_class().register_postfork_function(f, *args, **kwargs)


@uwsgi_postfork
def _do_postfork():
    for f, args, kwargs in [t for t in UWSGIApplicationStack.postfork_functions]:
        f(*args, **kwargs)
