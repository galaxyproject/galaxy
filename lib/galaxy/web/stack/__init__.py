"""Web application stack operations
"""
from __future__ import absolute_import

import inspect
import json
import logging
import os

# The uwsgi module is automatically injected by the parent uwsgi process and only exists that way.  If anything works,
# this is a uwsgi-managed process.
try:
    import uwsgi
except ImportError:
    uwsgi = None

import yaml
from six import string_types

from galaxy.util import unicodify
from galaxy.util.facts import get_facts
from galaxy.util.path import has_ext
from galaxy.util.properties import nice_config_parser
from .handlers import HANDLER_ASSIGNMENT_METHODS
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
        if app:
            log.debug("%s initialized", self.__class__.__name__)

    def _set_default_job_handler_assignment_methods(self, job_config, base_pool):
        """Override in subclasses to set default job handler assignment methods if not explicitly configured by the administrator.

        Called once per job_config.
        """
        pass

    def _init_job_handler_assignment_methods(self, job_config, base_pool):
        if not job_config.handler_assignment_methods_configured:
            self._set_default_job_handler_assignment_methods(job_config, base_pool)

    def _init_job_handler_subpools(self, job_config, base_pool):
        """Set up members of "subpools" ("base_pool.*") as handlers (including the base pool itself, if it exists).
        """
        for pool_name in self.configured_pools:
            if pool_name == base_pool:
                tag = job_config.DEFAULT_HANDLER_TAG
            elif pool_name.startswith(base_pool + '.'):
                tag = pool_name.replace(base_pool + '.', '', 1)
            else:
                continue
            # Pools are hierarchical (so that you can have e.g. workflow schedulers use the job handlers pool if no
            # workflow schedulers pool exists), so if a pool for a given tag has already been found higher in the
            # hierarchy, don't add members from a pool lower in the hierarchy.
            if tag not in job_config.pool_for_tag:
                if self.in_pool(pool_name):
                    job_config.is_handler = True
                for handler in self.pool_members(pool_name):
                    job_config.add_handler(handler, [tag])
                job_config.pool_for_tag[tag] = pool_name

    def init_job_handling(self, job_config):
        """Automatically add pools as handlers if they are named per predefined names and there is not an explicit
        job handler assignment configuration.

        Also automatically set the preferred assignment method if pool handlers are found and an assignment method is
        not explicitly configured by the administrator.
        """
        stack_assignment_methods_configured = False
        for base_pool in job_config.DEFAULT_BASE_HANDLER_POOLS:
            if self.has_base_pool(base_pool):
                if not stack_assignment_methods_configured:
                    self._init_job_handler_assignment_methods(job_config, base_pool)
                    stack_assignment_methods_configured = True
                self._init_job_handler_subpools(job_config, base_pool)

    def init_late_prefork(self):
        pass

    def log_startup(self):
        log.info("Galaxy server instance '%s' is running" % self.config.server_name)

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

    @property
    def configured_pools(self):
        return {}

    def has_base_pool(self, pool_name):
        return self.has_pool(pool_name) or any([pool.startswith(pool_name + '.') for pool in self.configured_pools])

    def has_pool(self, pool_name):
        return pool_name in self.configured_pools

    def in_pool(self, pool_name):
        return False

    def pool_members(self, pool_name):
        return None

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
        self.use_messaging = False
        self.dispatcher = ApplicationStackMessageDispatcher()
        self.transport = self.transport_class(app, stack=self, dispatcher=self.dispatcher)

    def init_late_prefork(self):
        self.transport.init_late_prefork()

    def start(self):
        super(MessageApplicationStack, self).start()
        if self.use_messaging and not self.running:
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
        if self.use_messaging and self.running:
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

    localhost_addrs = ('127.0.0.1', '[::1]')
    bind_all_addrs = ('', '0.0.0.0', '[::]')

    @staticmethod
    def _get_config_file(confs, loader, section):
        """uWSGI allows config merging, in which case the corresponding config file option will be a list.
        """
        conf = None
        if isinstance(confs, list):
            gconfs = [_ for _ in confs if os.path.exists(_) and section in loader(open(_))]
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

    @staticmethod
    def _socket_opt_to_str(opt, val):
        try:
            opt = unicodify(opt)
            val = unicodify(val)
            if val.startswith('='):
                val = unicodify(uwsgi.opt.get('shared-socket', [])[int(val.split('=')[1])])
            proto = opt if opt != 'socket' else 'uwsgi'
            if proto == 'uwsgi' and ':' not in val:
                return 'uwsgi://' + val
            else:
                proto = proto + '://'
                host, port = val.rsplit(':', 1)
                port = ':' + port.split(',', 1)[0]
            if host in UWSGIApplicationStack.bind_all_addrs:
                host = UWSGIApplicationStack.localhost_addrs[0]
            return proto + host + port
        except (IndexError, AttributeError):
            return '%s %s' % (opt, val)

    @staticmethod
    def _socket_opts():
        for opt in ('https', 'http', 'socket'):
            if opt in uwsgi.opt:
                val = uwsgi.opt[opt]
                if isinstance(val, list):
                    for v in val:
                        yield (opt, v)
                else:
                    yield (opt, val)

    @staticmethod
    def _serving_on():
        for opt, val in UWSGIApplicationStack._socket_opts():
            yield UWSGIApplicationStack._socket_opt_to_str(opt, val)

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
        self._farm_server_names_dict = None

        # If there's more than one farm *and* more than one farm will be using farm messaging, additional locks need to
        # be configured by the admin. This allows us to keep track of how many such farms are configured.
        self._lock_farms = set()

        super(UWSGIApplicationStack, self).__init__(app=app, config=config)

    def _set_default_job_handler_assignment_methods(self, job_config, base_pool):
        # Disable DB_SELF if a valid farm (pool) is configured. Use mule messaging unless the job_config doesn't allow
        # it (e.g. workflow scheduling manager), in which case, use DB_PREASSIGN.
        #
        # TODO MULTIPOOL: if there is no default in any base_pool (and no job_config.default_handler_id) then don't
        # remove DB_SELF
        conf_class_name = job_config.__class__.__name__
        remove_methods = [HANDLER_ASSIGNMENT_METHODS.DB_SELF]
        if (HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE not in job_config.UNSUPPORTED_HANDLER_ASSIGNMENT_METHODS):
            add_method = HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE
        else:
            add_method = HANDLER_ASSIGNMENT_METHODS.DB_PREASSIGN
            remove_methods.append(HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE)
        log.debug("%s: No job handler assignment methods were configured but a uWSGI farm named '%s' exists,"
                  " automatically enabling the '%s' assignment method", conf_class_name, base_pool, add_method)
        for m in remove_methods:
            try:
                job_config.handler_assignment_methods.remove(m)
                log.debug("%s: Removed '%s' from handler assignment methods due to use of mules", conf_class_name, m)
            except ValueError:
                pass
        if add_method not in job_config.handler_assignment_methods:
            job_config.handler_assignment_methods.insert(0, add_method)
        log.debug("%s: handler assignment methods updated to: %s", conf_class_name,
                  ', '.join(job_config.handler_assignment_methods))

    def _init_job_handler_assignment_methods(self, job_config, base_pool):
        super(UWSGIApplicationStack, self)._init_job_handler_assignment_methods(job_config, base_pool)
        # Determine if stack messaging should be enabled
        if HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE in job_config.handler_assignment_methods:
            self.use_messaging = True

    def _init_job_handler_subpools(self, job_config, base_pool):
        super(UWSGIApplicationStack, self)._init_job_handler_subpools(job_config, base_pool)
        # Count the required number of uWSGI locks
        if job_config.use_messaging:
            for pool_name in self.configured_pools:
                if (pool_name == base_pool or pool_name.startswith(base_pool + '.')):
                    self._lock_farms.add(pool_name)

    @property
    def _configured_mules(self):
        if self._mules_list is None:
            self._mules_list = _uwsgi_configured_mules()
        return self._mules_list

    @property
    def _is_mule(self):
        return uwsgi.mule_id() > 0

    @property
    def configured_pools(self):
        if self._farms_dict is None:
            self._farms_dict = {}
            farms = uwsgi.opt.get('farm', [])
            farms = farms if isinstance(farms, list) else [farms]
            for farm in farms:
                farm = unicodify(farm)
                name, mules = farm.split(':', 1)
                self._farms_dict[name] = [int(m) for m in mules.split(',')]
        return self._farms_dict

    @property
    def _farms(self):
        farms = []
        for farm, mules in self.configured_pools.items():
            if uwsgi.mule_id() in mules:
                farms.append(farm)
        return farms

    def _mule_index_in_farm(self, farm_name, mule_id=None):
        mule_id = mule_id or uwsgi.mule_id()
        try:
            mules = self.configured_pools[farm_name]
            return mules.index(mule_id)
        except (KeyError, ValueError):
            return -1

    @property
    def _farm_name(self):
        # TODO: to allow mules to be in multiple farms you'll need to start here
        try:
            return self._farms[0]
        except IndexError:
            return None

    @property
    def _farm_server_names(self):
        if self._farm_server_names_dict is None:
            self._farm_server_names_dict = {}
            for farm_name, mules in self.configured_pools.items():
                server_names = []
                facts = self.facts
                for mule in mules:
                    facts.update({
                        'pool_name': farm_name,
                        'server_id': mule,
                        'instance_id': self._mule_index_in_farm(farm_name, mule) + 1,
                    })
                    server_names.append(self.server_name_template.format(**facts))
                self._farm_server_names_dict[farm_name] = server_names
        return self._farm_server_names_dict

    @property
    def instance_id(self):
        if not self._is_mule:
            instance_id = uwsgi.worker_id()
        elif self._farm_name:
            return self._mule_index_in_farm(self._farm_name) + 1
        else:
            instance_id = uwsgi.mule_id()
        return instance_id

    def log_startup(self):
        msg = ["Galaxy server instance '%s' is running" % self.config.server_name]
        # Log the next messages when the first worker finishes starting. This
        # may not be the first to finish (so Galaxy could be serving already),
        # but it's a good approximation and gives the correct root_pid below
        # when there is no master process.
        if not self._is_mule and self.instance_id == 1:
            # We use the same text printed by Paste to not break scripts
            # grepping for this line. Here root_pid is the same that gets
            # written to file when using the --pidfile option of uwsgi
            root_pid = uwsgi.masterpid() or os.getpid()
            msg.append('Starting server in PID %d.' % root_pid)
            for s in UWSGIApplicationStack._serving_on():
                msg.append('serving on ' + s)
            if len(msg) == 1:
                msg.append('serving on unknown URL')
        log.info('\n'.join(msg))

    def start(self):
        # Does a generalized `is_worker` attribute make sense? Hard to say w/o other stack paradigms.
        if self._is_mule and self._farm_name:
            # used by main.py to send a shutdown message on termination
            os.environ['_GALAXY_UWSGI_FARM_NAMES'] = ','.join(self._farms)
        super(UWSGIApplicationStack, self).start()

    def in_pool(self, pool_name):
        if not self._is_mule:
            return False
        else:
            return pool_name in self._farms

    def pool_members(self, pool_name):
        return self._farm_server_names.get(pool_name, None)

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

    def _set_default_job_handler_assignment_methods(self, job_config, base_pool):
        # We will only get here if --attach-to-pool has been set so it is safe to assume that this handler is dynamic
        # and that we want to use one of the DB serialization methods.
        #
        # Disable DB_SELF if a valid pool is configured. Use DB "SKIP LOCKED" if the DB engine supports it, transaction
        # isolation if it doesn't, or DB_PREASSIGN if the job_config doesn't allow either.
        conf_class_name = job_config.__class__.__name__
        remove_methods = [HANDLER_ASSIGNMENT_METHODS.DB_SELF]
        dialect = self.app.model.session.bind.dialect
        if ((dialect.name == 'postgresql' and dialect.server_version_info >= (9, 5))
                or (dialect.name == 'mysql' and dialect.server_version_info >= (8, 0, 1))):
            add_method = HANDLER_ASSIGNMENT_METHODS.DB_SKIP_LOCKED
        else:
            HANDLER_ASSIGNMENT_METHODS.DB_TRANSACTION_ISOLATION
        if add_method in job_config.UNSUPPORTED_HANDLER_ASSIGNMENT_METHODS:
            remove_methods.append(add_method)
            add_method = HANDLER_ASSIGNMENT_METHODS.DB_PREASSIGN
        log.debug("%s: No job handler assignment methods were configured but this server is configured to attach to the"
                  " '%s' pool, automatically enabling the '%s' assignment method", conf_class_name, base_pool, add_method)
        for m in remove_methods:
            try:
                job_config.handler_assignment_methods.remove(m)
                log.debug("%s: Removed '%s' from handler assignment methods due to use of mules", conf_class_name, m)
            except ValueError:
                pass
        if add_method not in job_config.handler_assignment_methods:
            job_config.handler_assignment_methods.insert(0, add_method)
        log.debug("%s: handler assignment methods updated to: %s", conf_class_name,
                  ', '.join(job_config.handler_assignment_methods))

    def __init__(self, app=None, config=None):
        super(WeblessApplicationStack, self).__init__(app=app, config=config)
        if self.app and self.config and self.config.attach_to_pools:
            log.debug("Will attach to pool(s): %s", ', '.join(self.config.attach_to_pools))

    @property
    def configured_pools(self):
        return {p: self.config.server_name for p in self.config.attach_to_pools}

    def in_pool(self, pool_name):
        return pool_name in self.config.attach_to_pools

    def pool_members(self, pool_name):
        return (self.config.server_name,) if self.in_pool(pool_name) else None


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
