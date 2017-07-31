"""Web application stack operations
"""
from __future__ import print_function

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

    def process_in_pool(self, pool_name):
        return None

    def initialize_msg_handler(self, app):
        return None

    def send_msg(self, msg, dest):
        pass

    def set_postfork_server_name(self, app):
        pass


class UWSGIApplicationStack(ApplicationStack):
    """Interface to the uWSGI application stack. Supports running additional webless Galaxy workers as mules. Mules
    must be farmed to be communicable via uWSGI mule messaging, unfarmed mules are not supported.
    """
    name = 'uWSGI'
    prohibited_middleware = frozenset([
        'wrap_in_static',
        'EvalException',
    ])
    setup_jobs_with_msg = True

    postfork_functions = []
    handler_prefix = 'mule-handler-'

    # Define any static lock names here, additional locks will be appended for each configured farm's message handler
    _locks = []

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        cls.postfork_functions.append((f, args, kwargs))

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
            self._mules_list = [mules] if isinstance(mules, string_types) else mules
        return self._mules_list

    def __initialize_locks(self):
        num = int(uwsgi.opt.get('locks', 0)) + 1
        farms = self._farms.keys()
        need = len(farms)
        #need = len(filter(lambda x: x.startswith('LOCK_'), dir(self)))
        if num < need:
            raise RuntimeError('Need %i uWSGI locks but only %i exist(s): Set `locks = %i` in uWSGI configuration' % (need, num, need - 1))
            sys.exit(1)
        self._locks.extend(map(lambda x: 'RECV_MSG_FARM_' + x, farms))
        # This would be nice, but in my 2.0.15 uWSGI, the uwsgi module has no set_option function. And I don't know if it'd work.
        #if len(self.lock_map) > 1:
        #    uwsgi.set_option('locks', len(self.lock_map))
        #    log.debug('Created %s uWSGI locks' % len(self.lock_map))

    def __register_signal_handlers(self):
        for name in ('TERM', 'INT', 'HUP'):
            sig = getattr(signal, 'SIG%s' % name)
            signal.signal(sig, self._handle_signal)

    def __handle_msgs(self):
        while self.running:
            # We are going to do this a lot, so cache the lock number
            lock = self._farm_recv_msg_lock_num()
            try:
                self._lock(lock)
                log.debug('######## Mule %s acquired message receive lock, waiting for new message', uwsgi.mule_id())
                msg = uwsgi.farm_get_msg()
                log.debug('######## Mule %s received message: %s', uwsgi.mule_id(), msg)
                self._unlock(lock)
                self.msg_handler(msg)
            except:
                log.exception( "Exception in mule message handling" )
        log.info('uWSGI Mule (id: %s) message handler shutting down', uwsgi.mule_id())

    def __init__(self):
        super(UWSGIApplicationStack, self).__init__()
        self._farms_dict = None
        self._mules_list = None
        self.app = None
        self.running = False
        self.msg_handler = None
        self.msg_thread = None
        self.msg_thread = threading.Thread(name="UWSGIApplicationStack.mule_msg_thread", target=self.__handle_msgs)
        self.msg_thread.daemon = True
        self.__initialize_locks()

    def _lock(self, name_or_id):
        try:
            uwsgi.lock(name_or_id)
        except TypeError:
            uwsgi.lock(self._locks.index(name_or_id))

    def _unlock(self, name_or_id):
        try:
            uwsgi.unlock(name_or_id)
        except TypeError:
            uwsgi.unlock(self._locks.index(name_or_id))

    @property
    def _farm_name(self):
        for name, mules in self._farms.items():
            if uwsgi.mule_id() in mules:
                return name
        return None

    def _farm_recv_msg_lock_num(self):
        return self._locks.index('RECV_MSG_FARM_' + self._farm_name)

    def _handle_signal(self, signum, frame):
        if signum in (signal.SIGTERM, signal.SIGINT):
            log.info('######## Mule %s received SIGINT/SIGTERM, shutting down', uwsgi.mule_id())
            # This terminates the application loop in the handler entrypoint
            self.app.exit = True
        elif signum == signal.SIGHUP:
            log.debug('######## Mule %s received SIGHUP, restarting', uwsgi.mule_id())
            # uWSGI master will restart us
            self.app.exit = True

    def workers(self):
        return uwsgi.workers()

    def process_in_pool(self, pool_name):
        return self._farm_name == pool_name

    def initialize_msg_handler(self, app, handler_func):
        """ Post-fork initialization.
        """
        self.app = app
        self.running = True
        if not uwsgi.in_farm():
            raise RuntimeError('Mule %s is not in a farm! Set `farm = %s:%s` in uWSGI configuration'
                               % (uwsgi.mule_id(),
                                  app.config.job_handler_pool_name,
                                  ','.join(map(str, range(1, len(filter(lambda x: x.endswith('galaxy/web/stack/uwsgi_mule/handler.py'), self._mules)) + 1)))))
        self.__register_signal_handlers()
        self.msg_handler = handler_func
        self.msg_thread.start()
        log.info('######## Job handler mule started, mule id: %s, farm name: %s, handler id: %s', uwsgi.mule_id(), self._farm_name, self.app.config.server_name)

    def send_msg(self, msg, dest):
        # TODO: the handler farm name should be configurable
        #log.debug('################## sending message from mule %s: %s', uwsgi.mule_id(), msg)
        log.debug('######## Sending message to farm %s: %s', dest, msg)
        uwsgi.farm_msg(dest, msg)
        log.debug('######## Message sent')

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


def process_in_pool(pool_name):
    return application_stack_instance().process_in_pool(pool_name)


@uwsgi_postfork
def _do_postfork():
    for f, args, kwargs in [t for t in UWSGIApplicationStack.postfork_functions]:
        f(*args, **kwargs)
