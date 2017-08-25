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

from six import string_types

from .message import ApplicationStackMessage, ApplicationStackMessageDispatcher, JobHandlerMessage, decode
from .transport import ApplicationStackTransport, UWSGIFarmMessageTransport

from galaxy.util.bunch import Bunch
from galaxy.util.facts import get_facts


log = logging.getLogger(__name__)


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
    transport_class = ApplicationStackTransport
    log_filter_class = ApplicationStackLogFilter
    # TODO: this belongs in the pool configuration
    server_name_template = '{server_name}'
    default_app_name = 'main'

    # used both to route jobs to a pool with this name and indicate whether or
    # not a stack is using messaging for handler assignment
    pools = Bunch(
        JOB_HANDLERS = 'job-handlers',
    )

    @staticmethod
    def get_app_kwds(config_section, app_name=None, for_paste_app=False):
        # TODO: how to implement for Paste/webless
        return {}

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        f(*args, **kwargs)

    def __init__(self, app=None):
        self.app = app

    def start(self):
        # TODO: with a stack config the pools could be parsed here
        pass

    def allowed_middleware(self, middleware):
        if hasattr(middleware, '__name__'):
            middleware = middleware.__name__
        return middleware not in self.prohibited_middleware

    def workers(self):
        return []

    @property
    def pool_name(self):
        # TODO: ideally jobs would be mappable to handlers by pool name
        return None

    def has_pool(self, pool_name):
        return False

    def in_pool(self, pool_name):
        return False

    @property
    def facts(self):
        facts = get_facts(config=self.app.config)
        facts.update({'pool_name': self.pool_name})
        return facts

    def set_postfork_server_name(self, app):
        app.config.server_name = self.server_name_template.format(**self.facts)
        log.debug('server_name set to: %s', app.config.server_name)

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
        self.transport = self.transport_class(app, stack=self, dispatcher=self.dispatcher)

    def start(self):
        super(MessageApplicationStack, self).start()
        self.transport.start()

    def register_message_handler(self, func, name=None):
        self.dispatcher.register_func(func, name)
        self.transport.start_if_needed()

    def deregister_message_handler(self, func=None, name=None):
        self.dispatcher.deregister_func(func, name)
        self.transport.stop_if_unneeded()

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
    transport_class = UWSGIFarmMessageTransport
    log_filter_class = UWSGILogFilter
    server_name_template = '{server_name}.{server_id}'

    postfork_functions = []

    @staticmethod
    def get_app_kwds(config_section, app_name=None, for_paste_app=False):
        kwds = {
            'config_file': None,
            'config_section': config_section,
        }
        # used by webless mules started under uWSGI
        uwsgi_opt = uwsgi.opt
        app_section = 'app:%s' % app_name if app_name else 'app:%s' % self.default_app_name
        config_file = uwsgi_opt.get("yaml") or uwsgi_opt.get("json")
        # legacy, support loading ini uWSGI config without --ini-paste but with the app config under Paste's [app:main] section
        if config_file is None and uwsgi_opt.get("ini"):
            config_file = uwsgi_opt["ini"]
            parser = nice_config_parser(config_file)
            if not parser.has_section(config_section) and parser.has_section(app_section):
                kwds['config_section'] = app_section
        if config_file is None and for_paste_app:
            return None
        if config_file is None and uwsgi_opt.get("ini-paste"):
            config_file = uwsgi_opt.get("ini") or uwsgi_opt.get("ini-paste")
            kwds['config_section'] = app_section
        if config_file is None:
            return None
        kwds['config_file'] = config_file
        return kwds


    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        if uwsgi.mule_id() == 0:
            cls.postfork_functions.append((f, args, kwargs))
        else:
            # mules are forked from the master and run the master's postfork functions immediately before the forked
            # process is replaced. that is prevented in the _do_uwsgi_postfork function, and because programmed mules
            # are standalone non-forking processes, they should run postfork functions immediately
            f(*args, **kwargs)

    def __init__(self, app=None):
        self._farms_dict = None
        self._mules_list = None
        super(UWSGIApplicationStack, self).__init__(app=app)

    def __register_signal_handlers(self):
        for name in ('TERM', 'INT', 'HUP'):
            sig = getattr(signal, 'SIG%s' % name)
            signal.signal(sig, self._handle_signal)

    def _handle_signal(self, signum, frame):
        # uWSGI always sends SIGINT even if the master received SIGTERM
        if signum in (signal.SIGTERM, signal.SIGINT):
            log.info('Received SIGTERM/SIGINT, shutting down gracefully')
        elif signum == signal.SIGHUP:
            log.debug('Received SIGHUP, restarting')
        self.shutdown()
        # this terminates the application loop in the mule script, in the case of HUP, uWSGI will restart the mule
        self.app.exit = True

    @property
    def _configured_mules(self):
        if self._mules_list is None:
            self._mules_list = _uwsgi_configured_mules()
        return self._mules_list

    @property
    def _is_mule(self):
        return uwsgi.mule_id() > 0

    @property
    def _configured_farms(self):
        if self._farms_dict is None:
            self._farms_dict = {}
            farms = uwsgi.opt.get('farm', [])
            farms = [farms] if isinstance(farms, string_types) else farms
            for farm in farms:
                name, mules = farm.split(':', 1)
                self._farms_dict[name] = [int(m) for m in mules.split(',')]
        return self._farms_dict

    @property
    def _farms(self):
        farms = []
        for farm, mules in self._configured_farms.items():
            if uwsgi.mule_id() in mules:
                farms.append(farm)
        return farms

    @property
    def _farm_name(self):
        try:
            return self._farms[0]
        except IndexError:
            return None

    def start(self):
        # Does a generalized `is_worker` attribute make sense? Hard to say w/o other stack paradigms.
        if self._is_mule:
            self.__register_signal_handlers()
        super(UWSGIApplicationStack, self).start()

    def has_pool(self, pool_name):
        return pool_name in self._configured_farms

    def in_pool(self, pool_name):
        if not self._is_mule:
            return False
        else:
            return pool_name in self._farms

    def workers(self):
        return uwsgi.workers()

    @property
    def facts(self):
        facts = super(UWSGIApplicationStack, self).facts
        facts.update({'server_id': 'worker%s' % uwsgi.worker_id() if uwsgi.mule_id() == 0 else 'mule%s' % uwsgi.mule_id()})
        return facts

    def shutdown(self):
        super(UWSGIApplicationStack, self).shutdown()


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


def application_stack_instance(app=None):
    stack_class = application_stack_class()
    return stack_class(app=app)


def application_stack_log_filter():
    return application_stack_class().log_filter_class


def register_postfork_function(f, *args, **kwargs):
    application_stack_class().register_postfork_function(f, *args, **kwargs)


def get_app_kwds(config_section):
    return application_stack_class().get_app_kwds(config_section)


def _uwsgi_configured_mules():
    mules = uwsgi.opt.get('mule', [])
    return [mules] if isinstance(mules, string_types) or mules is True else mules


def _do_uwsgi_postfork():
    for i, mule in enumerate(_uwsgi_configured_mules()):
        if mule is not True and i + 1 == uwsgi.mule_id():
            # mules will inherit the postfork function list and call them immediately upon fork, but programmed mules
            # should not do that (they will call the postfork functions in-place as they start up after exec())
            UWSGIApplicationStack.postfork_functions = []
    for f, args, kwargs in [t for t in UWSGIApplicationStack.postfork_functions]:
        log.debug('Calling postfork function: %s', f)
        f(*args, **kwargs)


if uwsgi:
    uwsgi.post_fork_hook = _do_uwsgi_postfork
