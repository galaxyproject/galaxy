"""Web application stack operations
"""
from __future__ import absolute_import

import inspect
import json
import logging
import os

# The uwsgi module is automatically injected by the parent uwsgi
# process and only exists that way.  If anything works, this is a
# uwsgi-managed process.
try:
    import uwsgi
except ImportError:
    uwsgi = None

import yaml
from six import string_types

from galaxy.util.bunch import Bunch
from galaxy.util.facts import get_facts
from galaxy.util.path import has_ext
from galaxy.util.properties import nice_config_parser
from .message import ApplicationStackMessage, ApplicationStackMessageDispatcher
from .transport import ApplicationStackTransport, UWSGIFarmMessageTransport


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
    log_format = '%(name)s %(levelname)s %(asctime)s %(message)s'
    # TODO: this belongs in the pool configuration
    server_name_template = '{server_name}'
    default_app_name = 'main'

    # used both to route jobs to a pool with this name and indicate whether or
    # not a stack is using messaging for handler assignment
    pools = Bunch(
        JOB_HANDLERS='job-handlers',
    )

    @classmethod
    def log_filter(cls):
        return cls.log_filter_class()

    @classmethod
    def get_app_kwds(cls, config_section, app_name=None, for_paste_app=False):
        return {}

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        f(*args, **kwargs)

    def __init__(self, app=None, config=None):
        self.app = app
        self.config = config or (app and app.config)
        self.running = False

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
        facts = get_facts(config=self.config)
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
    def __init__(self, app=None, config=None):
        super(MessageApplicationStack, self).__init__(app=app, config=config)
        self.dispatcher = ApplicationStackMessageDispatcher()
        self.transport = self.transport_class(app, stack=self, dispatcher=self.dispatcher)

    def start(self):
        super(MessageApplicationStack, self).start()
        if not self.running:
            self.transport.start()
            self.running = True

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
        if self.running:
            log.info('Application stack interface shutting down')
            self.transport.shutdown()
            self.running = False


class UWSGIApplicationStack(MessageApplicationStack):
    """Interface to the uWSGI application stack. Supports running additional webless Galaxy workers as mules. Mules
    must be farmed to be communicable via uWSGI mule messaging, unfarmed mules are not supported.

    Note that mules will use this as their stack class even though they start with the "webless" loading point.
    """
    name = 'uWSGI'
    prohibited_middleware = frozenset([
        'wrap_in_static',
        'EvalException',
    ])
    transport_class = UWSGIFarmMessageTransport
    log_filter_class = UWSGILogFilter
    log_format = '%(name)s %(levelname)s %(asctime)s [p:%(process)s,w:%(worker_id)s,m:%(mule_id)s] [%(threadName)s] %(message)s'
    server_name_template = '{server_name}.{pool_name}.{instance_id}'

    postfork_functions = []

    @staticmethod
    def _get_config_file(confs, loader, section):
        """uWSGI allows config merging, in which case the corresponding config file option will be a list.
        """
        conf = None
        if isinstance(confs, list):
            gconfs = filter(lambda x: os.path.exists(x) and section in loader(open(x)), confs)
            if len(gconfs) == 1:
                conf = gconfs[0]
            elif len(gconfs) == 0:
                log.warning('Could not locate a config file containing a Galaxy config from: %s',
                            ', '.join(confs))
            else:
                log.warning('Multiple config files contain Galaxy configs, merging is not supported: %s',
                            ', '.join(gconfs))
        else:
            conf = confs
        return conf

    @classmethod
    def get_app_kwds(cls, config_section, app_name=None):
        kwds = {
            'config_file': None,
            'config_section': config_section,
        }
        uwsgi_opt = uwsgi.opt
        config_file = None
        # check for --set galaxy_config_file=<path>, this overrides whatever config file uWSGI was loaded with (which
        # may not actually include a Galaxy config)
        if uwsgi_opt.get("galaxy_config_file"):
            config_file = uwsgi_opt.get("galaxy_config_file")
        # check for --yaml or --json uWSGI config options next
        if config_file is None:
            config_file = (UWSGIApplicationStack._get_config_file(uwsgi_opt.get("yaml"), yaml.safe_load, config_section)
                           or UWSGIApplicationStack._get_config_file(uwsgi_opt.get("json"), json.load, config_section))
        # --ini and --ini-paste don't behave the same way, but this method will only be called by mules if the main
        # application was loaded with --ini-paste, so we can make some assumptions, most notably, uWSGI does not have
        # any way to set the app name when loading with paste.deploy:loadapp(), so hardcoding the alternate section
        # name to `app:main` is fine.
        has_ini_config = config_file is None and uwsgi_opt.get("ini") or uwsgi_opt.get("ini-paste")
        has_ini_config = has_ini_config or (config_file and has_ext(config_file, "ini", aliases=True, ignore="sample"))
        if has_ini_config:
            config_file = config_file or uwsgi_opt.get("ini") or uwsgi_opt.get("ini-paste")
            parser = nice_config_parser(config_file)
            if not parser.has_section(config_section) and parser.has_section('app:main'):
                kwds['config_section'] = 'app:main'
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

    def __init__(self, app=None, config=None):
        self._farms_dict = None
        self._mules_list = None
        super(UWSGIApplicationStack, self).__init__(app=app, config=config)

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

    def _mule_index_in_farm(self, farm_name):
        try:
            mules = self._configured_farms[farm_name]
            return mules.index(uwsgi.mule_id())
        except (KeyError, ValueError):
            return -1

    @property
    def _farm_name(self):
        try:
            return self._farms[0]
        except IndexError:
            return None

    @property
    def instance_id(self):
        if not self._is_mule:
            instance_id = uwsgi.worker_id()
        elif self._farm_name:
            return self._mule_index_in_farm(self._farm_name) + 1
        else:
            instance_id = uwsgi.mule_id()
        return instance_id

    def start(self):
        # Does a generalized `is_worker` attribute make sense? Hard to say w/o other stack paradigms.
        if self._is_mule and self._farm_name:
            # used by main.py to send a shutdown message on termination
            os.environ['_GALAXY_UWSGI_FARM_NAMES'] = ','.join(self._farms)
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
        if not self._is_mule:
            facts.update({
                'pool_name': 'web',
                'server_id': uwsgi.worker_id(),
            })
        else:
            facts.update({
                'pool_name': self._farm_name,
                'server_id': uwsgi.mule_id(),
            })
        facts['instance_id'] = self.instance_id
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


def application_stack_instance(app=None, config=None):
    stack_class = application_stack_class()
    return stack_class(app=app, config=config)


def application_stack_log_filter():
    return application_stack_class().log_filter_class()


def application_stack_log_formatter():
    return logging.Formatter(fmt=application_stack_class().log_format)


def register_postfork_function(f, *args, **kwargs):
    application_stack_class().register_postfork_function(f, *args, **kwargs)


def get_app_kwds(config_section, app_name=None):
    return application_stack_class().get_app_kwds(config_section, app_name=app_name)


def get_stack_facts(config=None):
    return application_stack_instance(config=config).facts


def _uwsgi_configured_mules():
    mules = uwsgi.opt.get('mule', [])
    return [mules] if isinstance(mules, string_types) or mules is True else mules


def _do_uwsgi_postfork():
    for i, mule in enumerate(_uwsgi_configured_mules()):
        if mule is not True and i + 1 == uwsgi.mule_id():
            # mules will inherit the postfork function list and call them immediately upon fork, but programmed mules
            # should not do that (they will call the postfork functions in-place as they start up after exec())
            UWSGIApplicationStack.postfork_functions = [(_mule_fixup, (), {})]
    for f, args, kwargs in [t for t in UWSGIApplicationStack.postfork_functions]:
        log.debug('Calling postfork function: %s', f)
        f(*args, **kwargs)


def _mule_fixup():
    from six.moves.urllib.request import install_opener
    install_opener(None)


if uwsgi:
    uwsgi.post_fork_hook = _do_uwsgi_postfork
