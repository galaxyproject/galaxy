"""Web application stack operations
"""
from __future__ import print_function

import inspect
import logging
import os
import threading

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

from galaxy import model


log = logging.getLogger(__name__)


class ApplicationStack(object):
    name = None
    prohibited_middleware = frozenset()
    setup_jobs_with_msg = False

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        f(*args, **kwargs)

    def workers(self):
        return []

    def allowed_middleware(self, middleware):
        if hasattr(middleware, '__name__'):
            middleware = middleware.__name__
        return middleware not in self.prohibited_middleware

    def process_is_handler(self, app):
        return None

    def initialize_handler(self, app):
        return None

    def send_msg(self, msg, dest):
        pass

    def set_postfork_server_name(self, app):
        pass


class UWSGIApplicationStack(ApplicationStack):
    name = 'uWSGI'
    prohibited_middleware = frozenset([
        'wrap_in_static',
        'EvalException',
    ])
    setup_jobs_with_msg = True

    postfork_functions = []
    handler_prefix = 'mule-handler-'

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        cls.postfork_functions.append((f, args, kwargs))

    def __handle_msgs(self):
        while self.running:
            try:
                log.debug('################ waiting for mule farm msg with mule %s', uwsgi.mule_id())
                # Hopefully farm_get_msg blocks like mule_get_msg does
                #self.msg_handler(uwsgi.farm_get_msg())
                #msg = uwsgi.farm_get_msg()
                msg = uwsgi.mule_get_msg()
                log.debug('################ received msg: %s', msg)
                self.msg_handler(msg)
            except:
                log.exception( "Exception in mule message handling" )

    def __init__(self):
        super(UWSGIApplicationStack, self).__init__()
        self.app = None
        self.running = False
        self.msg_handler = None
        self.msg_thread = threading.Thread(name="UWSGIApplicationStack.mule_msg_thread", target=self.__handle_msgs)
        self.msg_thread.daemon = True

    def workers(self):
        return uwsgi.workers()

    def process_is_handler(self, app):
        if app.config.server_name.startswith(UWSGIApplicationStack.handler_prefix):
            return True
        return False

    def initialize_handler(self, app):
        self.app = app
        self.running = True
        self.msg_handler = self.app.job_manager.job_queue.handle_msg
        self.msg_thread.start()

    def send_msg(self, msg, dest):
        # TODO: the handler farm name should be configurable
        log.debug('################## sending message from mule %s: %s', uwsgi.mule_id(), msg)
        #uwsgi.farm_msg(msg, dest)
        uwsgi.mule_msg(msg)
        log.debug('################## message sent')

    def terminate_handler(self):
        self.running = False

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


def process_is_handler(app):
    return application_stack_instance().process_is_handler(app)


@uwsgi_postfork
def _do_postfork():
    for f, args, kwargs in [t for t in UWSGIApplicationStack.postfork_functions]:
        f(*args, **kwargs)
