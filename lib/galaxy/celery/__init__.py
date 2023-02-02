import os
from functools import (
    lru_cache,
    wraps,
)
from multiprocessing import get_context
from threading import local
from typing import (
    Any,
    Callable,
    Dict,
)

import pebble
from celery import (
    Celery,
    shared_task,
)
from celery.signals import (
    worker_init,
    worker_shutting_down,
)
from kombu import serialization

from galaxy.config import Configuration
from galaxy.main_config import find_config
from galaxy.util import ExecutionTimer
from galaxy.util.custom_logging import get_logger
from galaxy.util.properties import load_app_properties
from ._serialization import (
    schema_dumps,
    schema_loads,
)

log = get_logger(__name__)

MAIN_TASK_MODULE = "galaxy.celery.tasks"
DEFAULT_TASK_QUEUE = "galaxy.internal"
TASKS_MODULES = [MAIN_TASK_MODULE]
PYDANTIC_AWARE_SERIALIZER_NAME = "pydantic-aware-json"

APP_LOCAL = local()

serialization.register(
    PYDANTIC_AWARE_SERIALIZER_NAME, encoder=schema_dumps, decoder=schema_loads, content_type="application/json"
)


class GalaxyCelery(Celery):
    fork_pool: pebble.ProcessPool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def gen_task_name(self, name, module):
        module = self.trim_module_name(module)
        return super().gen_task_name(name, module)

    def trim_module_name(self, module):
        """
        Drop "celery.tasks" infix for less verbose task names:
        - galaxy.celery.tasks.do_foo >> galaxy.do_foo
        - galaxy.celery.tasks.subtasks.do_fuz >> galaxy.subtasks.do_fuz
        """
        if module.startswith("galaxy.celery.tasks"):
            module = f"galaxy{module[19:]}"
        return module


def set_thread_app(app):
    APP_LOCAL.app = app


def get_galaxy_app():
    try:
        return APP_LOCAL.app
    except AttributeError:
        import galaxy.app

        if galaxy.app.app:
            return galaxy.app.app
    return build_app()


@lru_cache(maxsize=1)
def build_app():
    kwargs = get_app_properties()
    if kwargs:
        kwargs["check_migrate_databases"] = False
        kwargs["use_display_applications"] = False
        kwargs["use_converters"] = False
        import galaxy.app

        galaxy_app = galaxy.app.GalaxyManagerApplication(configure_logging=False, **kwargs)
        return galaxy_app


@lru_cache(maxsize=1)
def get_app_properties():
    config_file = os.environ.get("GALAXY_CONFIG_FILE")
    galaxy_root_dir = os.environ.get("GALAXY_ROOT_DIR")
    if not config_file and galaxy_root_dir:
        config_file = find_config(config_file, galaxy_root_dir)
    if config_file:
        properties = load_app_properties(
            config_file=os.path.abspath(config_file),
            config_section="galaxy",
        )
        if galaxy_root_dir:
            properties["root_dir"] = galaxy_root_dir
        return properties


@lru_cache(maxsize=1)
def get_config():
    kwargs = get_app_properties() or {}
    kwargs["override_tempdir"] = False
    return Configuration(**kwargs)


def init_fork_pool():
    # Do slow imports when workers boot.
    from galaxy.datatypes import registry  # noqa: F401
    from galaxy.metadata import set_metadata  # noqa: F401


@worker_init.connect
def setup_worker_pool(sender=None, conf=None, instance=None, **kwargs):
    context = get_context("forkserver")
    celery_app.fork_pool = pebble.ProcessPool(
        max_workers=sender.concurrency, max_tasks=100, initializer=init_fork_pool, context=context
    )


@worker_shutting_down.connect
def tear_down_pool(sig, how, exitcode, **kwargs):
    log.debug("shutting down forkserver pool")
    celery_app.fork_pool.stop()
    celery_app.fork_pool.join(timeout=5)


def galaxy_task(*args, action=None, **celery_task_kwd):
    if "serializer" not in celery_task_kwd:
        celery_task_kwd["serializer"] = PYDANTIC_AWARE_SERIALIZER_NAME

    def decorate(func: Callable):
        @shared_task(**celery_task_kwd)
        @wraps(func)
        def wrapper(*args, **kwds):
            app = get_galaxy_app()
            assert app

            desc = func.__name__
            if action is not None:
                desc += f" to {action}"

            try:
                timer = app.execution_timer_factory.get_timer("internals.tasks.{func.__name__}", desc)
            except AttributeError:
                timer = ExecutionTimer()

            try:
                rval = app.magic_partial(func)(*args, **kwds)
                message = f"Successfully executed Celery task {desc} {timer}"
                log.info(message)
                return rval
            except Exception:
                log.warning(f"Celery task execution failed for {desc} {timer}")
                raise

        return wrapper

    if len(args) == 1 and callable(args[0]):
        return decorate(args[0])
    else:
        return decorate


def init_celery_app():
    celery_app_kwd: Dict[str, Any] = {
        "include": TASKS_MODULES,
        "task_default_queue": DEFAULT_TASK_QUEUE,
        "task_create_missing_queues": True,
        "timezone": "UTC",
    }
    celery_app = GalaxyCelery("galaxy", **celery_app_kwd)
    celery_app.set_default()
    config = get_config()
    config_celery_app(config, celery_app)
    setup_periodic_tasks(config, celery_app)
    return celery_app


def config_celery_app(config, celery_app):
    # Apply settings from galaxy's config
    if config.celery_conf:
        celery_app.conf.update(config.celery_conf)
    # Handle special cases
    if not celery_app.conf.broker_url:
        celery_app.conf.broker_url = config.amqp_internal_connection


def setup_periodic_tasks(config, celery_app):
    def schedule_task(task, interval):
        if interval > 0:
            task_key = task.replace("_", "-")
            module_name = celery_app.trim_module_name(MAIN_TASK_MODULE)
            task_name = f"{module_name}.{task}"
            beat_schedule[task_key] = {
                "task": task_name,
                "schedule": interval,
            }

    beat_schedule: Dict[str, Dict[str, Any]] = {}
    schedule_task("prune_history_audit_table", config.history_audit_table_prune_interval)
    schedule_task("cleanup_short_term_storage", config.short_term_storage_cleanup_interval)

    if beat_schedule:
        celery_app.conf.beat_schedule = beat_schedule


celery_app = init_celery_app()
