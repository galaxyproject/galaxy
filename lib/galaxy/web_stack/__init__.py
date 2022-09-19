"""Web application stack operations."""

import logging
import multiprocessing
import os
import sys
import threading
from typing import (
    Callable,
    FrozenSet,
    List,
    Optional,
    Type,
)

from galaxy.util.facts import get_facts
from .handlers import HANDLER_ASSIGNMENT_METHODS

log = logging.getLogger(__name__)


class ApplicationStackLogFilter(logging.Filter):
    def filter(self, record):
        return True


class ApplicationStack:
    name: Optional[str] = None
    prohibited_middleware: FrozenSet[str] = frozenset()
    log_filter_class: Type[logging.Filter] = ApplicationStackLogFilter
    log_format = "%(name)s %(levelname)s %(asctime)s [pN:%(processName)s,p:%(process)d,tN:%(threadName)s] %(message)s"
    # TODO: this belongs in the pool configuration
    server_name_template = "{server_name}"
    default_app_name = "main"

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
        self._supports_returning = None
        self._supports_skip_locked = None
        self._preferred_handler_assignment_method = None
        multiprocessing.current_process().name = getattr(self.config, "server_name", "main")
        if app:
            log.debug("%s initialized", self.__class__.__name__)

    def supports_returning(self):
        if self._supports_returning is None:
            job_table = self.app.model.Job.__table__
            stmt = job_table.update().where(job_table.c.id == -1).returning(job_table.c.id)
            try:
                self.app.model.session.execute(stmt)
                self._supports_returning = True
            except Exception:
                self._supports_returning = False
        return self._supports_returning

    def supports_skip_locked(self):
        if self._supports_skip_locked is None:
            job_table = self.app.model.Job.__table__
            stmt = job_table.select().where(job_table.c.id == -1).with_for_update(skip_locked=True)
            try:
                self.app.model.session.execute(stmt)
                self._supports_skip_locked = True
            except Exception:
                self._supports_skip_locked = False
        return self._supports_skip_locked

    def get_preferred_handler_assignment_method(self):
        if self._preferred_handler_assignment_method is None:
            if self.app.application_stack.supports_skip_locked():
                self._preferred_handler_assignment_method = HANDLER_ASSIGNMENT_METHODS.DB_SKIP_LOCKED
            else:
                log.debug(
                    "Database does not support WITH FOR UPDATE statement, cannot use DB-SKIP-LOCKED handler assignment"
                )
                self._preferred_handler_assignment_method = HANDLER_ASSIGNMENT_METHODS.DB_TRANSACTION_ISOLATION
        return self._preferred_handler_assignment_method

    def _set_default_job_handler_assignment_methods(self, job_config, base_pool):
        """Override in subclasses to set default job handler assignment methods if not explicitly configured by the administrator.

        Called once per job_config.
        """

    def _init_job_handler_assignment_methods(self, job_config, base_pool):
        if not job_config.handler_assignment_methods_configured:
            self._set_default_job_handler_assignment_methods(job_config, base_pool)

    def _init_job_handler_subpools(self, job_config, base_pool):
        """Set up members of "subpools" ("base_pool.*") as handlers (including the base pool itself, if it exists)."""
        for pool_name in self.configured_pools:
            if pool_name == base_pool:
                tag = job_config.DEFAULT_HANDLER_TAG
            elif pool_name.startswith(f"{base_pool}."):
                tag = pool_name.replace(f"{base_pool}.", "", 1)
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
        log.info(f"Galaxy server instance '{self.config.server_name}' is running")

    def start(self):
        # TODO: with a stack config the pools could be parsed here
        pass

    def allowed_middleware(self, middleware):
        if hasattr(middleware, "__name__"):
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
        return self.has_pool(pool_name) or any(pool.startswith(f"{pool_name}.") for pool in self.configured_pools)

    def has_pool(self, pool_name):
        return pool_name in self.configured_pools

    def in_pool(self, pool_name):
        return False

    def pool_members(self, pool_name):
        return None

    @property
    def facts(self):
        facts = get_facts(config=self.config)
        facts.update({"pool_name": self.pool_name})
        return facts

    def set_postfork_server_name(self, app):
        new_server_name = self.server_name_template.format(**self.facts)
        if "GUNICORN_WORKER_ID" in os.environ:
            new_server_name = f"{new_server_name}.{os.environ['GUNICORN_WORKER_ID']}"
        multiprocessing.current_process().name = app.config.server_name = new_server_name
        log.debug("server_name set to: %s", new_server_name)

    def shutdown(self):
        pass


class WebApplicationStack(ApplicationStack):
    name = "Web"


class GunicornApplicationStack(ApplicationStack):
    name = "Gunicorn"
    do_post_fork = "--preload" in os.environ.get("GUNICORN_CMD_ARGS", "") or "--preload" in sys.argv
    postfork_functions: List[Callable] = []
    # Will be set to True by external hook
    late_postfork_event = threading.Event()
    late_postfork_thread: threading.Thread

    @classmethod
    def register_postfork_function(cls, f, *args, **kwargs):
        # do_post_fork determines if we need to run postfork functions
        if cls.do_post_fork:
            # if so, we call ApplicationStack.late_postfork once after forking ...
            if not cls.postfork_functions:
                os.register_at_fork(after_in_child=cls.late_postfork)
            # ... and store everything we need to run in ApplicationStack.postfork_functions
            cls.postfork_functions.append(lambda: f(*args, **kwargs))
        else:
            f(*args, **kwargs)

    @classmethod
    def run_postfork(cls):
        cls.late_postfork_event.wait(1)
        for f in cls.postfork_functions:
            f()

    @classmethod
    def late_postfork(cls):
        # We can't run postfork functions immediately, because this is before the gunicorn `post_fork` hook runs,
        # and we depend on the `post_fork` hook to set a worker id.
        cls.late_postfork_thread = threading.Thread(target=cls.run_postfork)
        cls.late_postfork_thread.start()

    def log_startup(self):
        msg = [f"Galaxy server instance '{self.config.server_name}' is running"]
        if "GUNICORN_LISTENERS" in os.environ:
            msg.append(f'serving on {os.environ["GUNICORN_LISTENERS"]}')
        log.info("\n".join(msg))


class WeblessApplicationStack(ApplicationStack):
    name = "Webless"

    def _set_default_job_handler_assignment_methods(self, job_config, base_pool):
        # We will only get here if --attach-to-pool has been set so it is safe to assume that this handler is dynamic
        # and that we want to use one of the DB serialization methods.
        #
        # Disable DB_SELF if a valid pool is configured. Use DB "SKIP LOCKED" if the DB engine supports it, transaction
        # isolation if it doesn't, or DB_PREASSIGN if the job_config doesn't allow either.
        conf_class_name = job_config.__class__.__name__
        remove_methods = [HANDLER_ASSIGNMENT_METHODS.DB_SELF]
        add_method = self.get_preferred_handler_assignment_method()
        log.debug(
            "%s: No job handler assignment methods were configured but this server is configured to attach to the"
            " '%s' pool, automatically enabling the '%s' assignment method",
            conf_class_name,
            base_pool,
            add_method,
        )
        for m in remove_methods:
            try:
                job_config.handler_assignment_methods.remove(m)
                log.debug(
                    "%s: Removed '%s' from handler assignment methods due to use of --attach-to-pool",
                    conf_class_name,
                    m,
                )
            except ValueError:
                pass
        if add_method not in job_config.handler_assignment_methods:
            job_config.handler_assignment_methods.insert(0, add_method)
        log.debug(
            "%s: handler assignment methods updated to: %s",
            conf_class_name,
            ", ".join(job_config.handler_assignment_methods),
        )

    def __init__(self, app=None, config=None):
        super().__init__(app=app, config=config)
        if self.app and self.config and self.config.attach_to_pools:
            log.debug("Will attach to pool(s): %s", ", ".join(self.config.attach_to_pools))

    @property
    def configured_pools(self):
        return {p: self.config.server_name for p in self.config.attach_to_pools}

    def in_pool(self, pool_name):
        return pool_name in self.config.attach_to_pools

    def pool_members(self, pool_name):
        return (self.config.server_name,) if self.in_pool(pool_name) else None


def application_stack_class() -> Type[ApplicationStack]:
    """Returns the correct ApplicationStack class for the stack under which
    this Galaxy process is running.
    """
    if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
        return GunicornApplicationStack
    elif os.environ.get("IS_WEBAPP") == "1":
        return WebApplicationStack
    return WeblessApplicationStack


def application_stack_instance(app=None, config=None) -> ApplicationStack:
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
