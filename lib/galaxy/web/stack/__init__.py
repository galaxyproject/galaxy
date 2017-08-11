"""Web application stack operations
"""
from __future__ import absolute_import, print_function

import inspect
import logging
import os
import signal
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

from six import string_types

from .message import ApplicationStackMessage, JobHandlerMessage, decode
from .transport import ApplicationStackTransport, UWSGIFarmMessageTransport


log = logging.getLogger(__name__)


class ApplicationStackMessageDispatcher(object):
    def __init__(self):
        self.__funcs = {}

    def __func_name(self, func, name):
        if not name:
            name = func.__name__
        return name

    def register_func(self, func, name=None):
        name = self.__func_name(func, name)
        self.__funcs[name] = func

    def deregister_func(self, func=None, name=None):
        name = self.__func_name(func, name)
        del self.__func[name]

    @property
    def handler_count(self):
        return len(self.__funcs)

    def dispatch(self, msg_str):
        msg = decode(msg_str)
        try:
            msg.validate()
        except AssertionError as exc:
            log.error('######## Invalid message received: %s, error: %s', msg_str, exc)
            return
        if msg.target not in self.__funcs:
            log.error("######## Received message with target '%s' but no functions were registered with that name. Params were: %s", msg.target, msg.params)
        else:
            self.__funcs[msg.target](msg)


class ApplicationStackLogFilter(logging.Filter):
    def filter(self, record):
        record.worker_id = None
        record.mule_id = None
        return True


class UWSGILogFilter(logging.Filter):
    def filter(self, record):
        record.worker_id = uwsgi.worker_id()
        record.mule_id = uwsgi.mule_id()
        return True


class ApplicationStack(object):
    name = None
    prohibited_middleware = frozenset()
    # TODO: this is a fairly clunky way of handling these cases
    setup_jobs_with_msg = False # used in galaxy.jobs.manager to determine whether jobs should be sent via message
    handle_jobs = False         # used by galaxy.jobs to determine whether this process handles jobs

    transport_class = ApplicationStackTransport
    log_filter_class = ApplicationStackLogFilter

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        f(*args, **kwargs)

    def __init__(self, app=None):
        self.app = app

    def start(self):
        pass

    # FIXME: used?
    def workers(self):
        return []

    def allowed_middleware(self, middleware):
        if hasattr(middleware, '__name__'):
            middleware = middleware.__name__
        return middleware not in self.prohibited_middleware

    def set_postfork_server_name(self, app):
        pass

    def process_in_pool(self, pool_name):
        return None

    def register_message_handler(self, func, name=None):
        pass

    def deregister_message_handler(self, func=None, name=None):
        pass

    def send_message(self, dest, msg=None, target=None, params=None, **kwargs):
        pass

    def shutdown(self):
        pass


class MessageApplicationStack(ApplicationStack):
    def __init__(self, app=None):
        super(MessageApplicationStack, self).__init__(app=app)
        self.dispatcher = ApplicationStackMessageDispatcher()
        self.transport = self.transport_class(app, dispatcher=self.dispatcher)
        #if app:
        #    log.debug('######## registering self.start')
        #    self.register_postfork_function(self.start)

    def start(self):
        self.transport.start()

    def register_message_handler(self, func, name=None):
        self.dispatcher.register_func(func, name)
        self.transport.start_if_needed()

    def deregister_message_handler(self, func=None, name=None):
        self.dispatcher.deregister_func(func, name)
        self.transport.shutdown_if_needed()

    def send_message(self, dest, msg=None, target=None, params=None, **kwargs):
        assert msg is not None or target is not None, "Either 'msg' or 'target' parameters must be set"
        if not msg:
            msg = ApplicationStackMessage(
                target=target,
                params=params,
                **kwargs
            )
        self.transport.send_message(msg.encode(), dest)

    def shutdown(self):
        self.transport.shutdown()


class UWSGIApplicationStack(MessageApplicationStack):
    """Interface to the uWSGI application stack. Supports running additional webless Galaxy workers as mules. Mules
    must be farmed to be communicable via uWSGI mule messaging, unfarmed mules are not supported.
    """
    name = 'uWSGI'
    prohibited_middleware = frozenset([
        'wrap_in_static',
        'EvalException',
    ])
    setup_jobs_with_msg = True

    transport_class = UWSGIFarmMessageTransport
    log_filter_class = UWSGILogFilter
    # FIXME: this is copied into UWSGIFarmMessageTransport
    shutdown_msg = '__SHUTDOWN__'
    postfork_functions = []
    # TODO: used?
    handler_prefix = 'mule-handler-'

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        if uwsgi.mule_id() == 0:
            cls.postfork_functions.append((f, args, kwargs))
        else:
            # mules are forked from the master and run the master's postfork functions immediately before the forked
            # process is replaced. that is prevented in the _do_uwsgi_postfork function, and because mules are
            # standalone non-forking processes, they should run postfork functions immediately
            f(*args, **kwargs)

    def __init__(self, app=None):
        super(UWSGIApplicationStack, self).__init__(app=app)
        self._farms_dict = None
        self._mules_list = None
        self._is_mule = None

    def __register_signal_handlers(self):
        for name in ('TERM', 'INT', 'HUP'):
            log.debug('######## registered signal handler for SIG%s', name)
            sig = getattr(signal, 'SIG%s' % name)
            signal.signal(sig, self._handle_signal)

    def _handle_signal(self, signum, frame):
        if signum == signal.SIGTERM:
            log.info('######## Mule %s received SIGTERM, shutting down gracefully', uwsgi.mule_id())
            self.shutdown()
        elif signum == signal.SIGINT:
            log.info('######## Mule %s received SIGINT, shutting down immediately', uwsgi.mule_id())
            self.shutdown()
            ## This terminates the application loop in the handler entrypoint
            #self.app.exit = True
        elif signum == signal.SIGHUP:
            log.debug('######## Mule %s received SIGHUP, restarting', uwsgi.mule_id())
            #self.shutdown()
            ## uWSGI master will restart us
            #self.app.exit = True

    # FIXME: these are copied into UWSGIFarmMessageTransport
    @property
    def _farms(self):
        if self._farms_dict is None:
            self._farms_dict = {}
            farms = uwsgi.opt.get('farm', [])
            farms = [farms] if isinstance(farms, string_types) else farms
            for farm in farms:
                name, mules = farm.split(':', 1)
                self._farms_dict[name] = [int(m) for m in mules.split(',')]
        return self._farms_dict

    @property
    def _mules(self):
        if self._mules_list is None:
            self._mules_list = []
            mules = uwsgi.opt.get('mule', [])
            self._mules_list = [mules] if isinstance(mules, string_types) or mules is True else mules
        return self._mules_list

    def start(self):
        self._is_mule = uwsgi.mule_id() > 0
        if self._is_mule:
            self.__register_signal_handlers()
        super(UWSGIApplicationStack, self).start()

    def set_postfork_server_name(self, app):
        if uwsgi.mule_id() == 0:
            app.config.server_name += ".worker%d" % uwsgi.worker_id()
        else:
            app.config.server_name += ".mule%d" % uwsgi.mule_id()

    # FIXME: used?
    def workers(self):
        return uwsgi.workers()

    def process_in_pool(self, pool_name):
        return self.transport._farm_name == pool_name

    def shutdown(self):
        log.debug('######## STACK SHUTDOWN CALLED')
        super(UWSGIApplicationStack, self).shutdown()
        # FIXME: blech
        #if not self._is_mule:
        #    for farm in self._farms:
        #        for mule in self._mules:
        #            # This will possibly generate more than we need, but that's ok
        #            self.transport.send_message(self.shutdown_msg, farm)


class PasteApplicationStack(ApplicationStack):
    name = 'Python Paste'
    handle_jobs = True


class WeblessApplicationStack(ApplicationStack):
    name = 'Webless'
    handle_jobs = True


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


def application_stack_instance(app=None):
    stack_class = application_stack_class()
    return stack_class(app=app)


def application_stack_log_filter():
    return application_stack_class().log_filter_class


def register_postfork_function(f, *args, **kwargs):
    application_stack_class().register_postfork_function(f, *args, **kwargs)


def process_in_pool(pool_name):
    return application_stack_instance().process_in_pool(pool_name)


@uwsgi_postfork
def _do_uwsgi_postfork():
    import os
    log.debug('######## postfork called, pid %s mule %s functions are: %s' % (os.getpid(), uwsgi.mule_id(), UWSGIApplicationStack.postfork_functions))
    #if uwsgi.mule_id() > 0:
    #    # mules will inherit the postfork function list and call them immediately upon fork, but should not do that
    #    UWSGIApplicationStack.postfork_functions = []
    for f, args, kwargs in [t for t in UWSGIApplicationStack.postfork_functions]:
        f(*args, **kwargs)
