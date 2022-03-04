import os
from functools import (
    lru_cache,
    wraps,
)
from threading import local
from typing import (
    Any,
    Dict,
)

from celery import (
    Celery,
    shared_task,
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
TASKS_MODULES = [MAIN_TASK_MODULE]
PYDANTIC_AWARE_SERIALIER_NAME = "pydantic-aware-json"

APP_LOCAL = local()

serialization.register(
    PYDANTIC_AWARE_SERIALIER_NAME, encoder=schema_dumps, decoder=schema_loads, content_type="application/json"
)


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
    kwargs = get_app_properties()
    if kwargs:
        kwargs["override_tempdir"] = False
        return Configuration(**kwargs)


def get_broker():
    config = get_config()
    if config:
        return config.celery_broker or config.amqp_internal_connection


def get_backend():
    config = get_config()
    if config:
        return config.celery_backend


def get_history_audit_table_prune_interval():
    config = get_config()
    if config:
        return config.history_audit_table_prune_interval
    else:
        return 3600


broker = get_broker()
backend = get_backend()
celery_app_kwd: Dict[str, Any] = {
    "broker": broker,
    "include": TASKS_MODULES,
}
if backend:
    celery_app_kwd["backend"] = backend

celery_app = Celery("galaxy", **celery_app_kwd)
prune_interval = get_history_audit_table_prune_interval()
if prune_interval > 0:
    celery_app.conf.beat_schedule = {
        "prune-history-audit-table": {
            "task": "galaxy.celery.tasks.prune_history_audit_table",
            "schedule": prune_interval,
        },
    }
celery_app.conf.timezone = "UTC"


def galaxy_task(*args, action=None, **celery_task_kwd):
    if "serializer" not in celery_task_kwd:
        celery_task_kwd["serializer"] = PYDANTIC_AWARE_SERIALIER_NAME

    def decorate(func):
        @shared_task(**celery_task_kwd)
        @wraps(func)
        def wrapper(*args, **kwds):
            app = get_galaxy_app()
            assert app
            desc = func.__name__
            if action is not None:
                desc += f" to {action}"
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


if __name__ == "__main__":
    celery_app.start()
