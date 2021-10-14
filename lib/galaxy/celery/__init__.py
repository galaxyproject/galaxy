import os
from functools import (
    lru_cache,
    wraps,
)
from typing import (
    Any,
    Dict,
)

from celery import (
    Celery,
    shared_task,
)
from kombu import serialization
from lagom import magic_bind_to_container

from galaxy.config import Configuration
from galaxy.main_config import find_config
from galaxy.util.custom_logging import get_logger
from galaxy.util.properties import load_app_properties
from ._serialization import (
    schema_dumps,
    schema_loads,
)

log = get_logger(__name__)

MAIN_TASK_MODULE = "galaxy.celery.tasks"
TASKS_MODULES = [MAIN_TASK_MODULE]


@lru_cache(maxsize=1)
def get_galaxy_app():
    import galaxy.app

    if galaxy.app.app:
        return galaxy.app.app
    kwargs = get_app_properties()
    if kwargs:
        kwargs["check_migrate_databases"] = False
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


CELERY_TASKS = []
PYDANTIC_AWARE_SERIALIER_NAME = "pydantic-aware-json"


serialization.register(
    PYDANTIC_AWARE_SERIALIER_NAME, encoder=schema_dumps, decoder=schema_loads, content_type="application/json"
)


def galaxy_task(*args, **celery_task_kwd):
    if "serializer" not in celery_task_kwd:
        celery_task_kwd["serializer"] = PYDANTIC_AWARE_SERIALIER_NAME

    def decorate(func):
        CELERY_TASKS.append(func.__name__)

        @shared_task(**celery_task_kwd)
        @wraps(func)
        def wrapper(*args, **kwds):
            app = get_galaxy_app()
            assert app
            return magic_bind_to_container(app)(func)(*args, **kwds)

        return wrapper

    if len(args) == 1 and callable(args[0]):
        return decorate(args[0])
    else:
        return decorate


if __name__ == "__main__":
    celery_app.start()
