import os
from functools import lru_cache
from threading import local
from typing import Any, Dict

from celery import Celery

from galaxy.config import Configuration
from galaxy.main_config import find_config
from galaxy.util.custom_logging import get_logger
from galaxy.util.properties import load_app_properties

log = get_logger(__name__)

MAIN_TASK_MODULE = 'galaxy.celery.tasks'
TASKS_MODULES = [MAIN_TASK_MODULE]

APP_LOCAL = local()


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
        kwargs['check_migrate_tools'] = False
        kwargs['check_migrate_databases'] = False
        import galaxy.app
        galaxy_app = galaxy.app.GalaxyManagerApplication(configure_logging=False, **kwargs)
        return galaxy_app


@lru_cache(maxsize=1)
def get_app_properties():
    config_file = os.environ.get("GALAXY_CONFIG_FILE")
    if not config_file:
        galaxy_root_dir = os.environ.get('GALAXY_ROOT_DIR')
        if galaxy_root_dir:
            config_file = find_config(config_file, galaxy_root_dir)
    if config_file:
        return load_app_properties(
            config_file=os.path.abspath(config_file),
            config_section='galaxy',
        )


@lru_cache(maxsize=1)
def get_config():
    kwargs = get_app_properties()
    if kwargs:
        kwargs['override_tempdir'] = False
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


def get_cleanup_short_term_storage_interval():
    config = get_config()
    if config:
        return config.short_term_storage_cleanup_interval
    else:
        return 3600


broker = get_broker()
backend = get_backend()
celery_app_kwd: Dict[str, Any] = {
    'broker': broker,
    'include': TASKS_MODULES,
}
if backend:
    celery_app_kwd["backend"] = backend

celery_app = Celery('galaxy', **celery_app_kwd)

# setup cron like tasks...
beat_schedule: Dict[str, Dict[str, Any]] = {}

prune_interval = get_history_audit_table_prune_interval()
if prune_interval > 0:
    beat_schedule['prune-history-audit-table'] = {
        'task': f'{MAIN_TASK_MODULE}.prune_history_audit_table',
        'schedule': prune_interval,
    }

cleanup_interval = get_cleanup_short_term_storage_interval()
if cleanup_interval > 0:
    beat_schedule['cleanup-short-term-storage'] = {
        'task': f'{MAIN_TASK_MODULE}.cleanup_short_term_storage',
        'schedule': cleanup_interval
    }

if beat_schedule:
    celery_app.conf.beat_schedule = beat_schedule
celery_app.conf.timezone = 'UTC'


if __name__ == '__main__':
    celery_app.start()
