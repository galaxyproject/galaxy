import os
from functools import lru_cache

from celery import Celery

from galaxy.config import Configuration
from galaxy.main_config import find_config
from galaxy.util.custom_logging import get_logger
from galaxy.util.properties import load_app_properties

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_galaxy_app():
    import galaxy.app
    if galaxy.app.app:
        return galaxy.app.app
    kwargs = get_app_properties()
    if kwargs:
        kwargs['check_migrate_tools'] = False
        kwargs['check_migrate_databases'] = False
        galaxy_app = galaxy.app.GalaxyManagerApplication(configure_logging=False, **kwargs)
        return galaxy_app


@lru_cache(maxsize=1)
def get_app_properties():
    config_file = os.environ.get("GALAXY_CONFIG_FILE")
    galaxy_root_dir = os.environ.get('GALAXY_ROOT_DIR')
    if not config_file and galaxy_root_dir:
        config_file = find_config(config_file, galaxy_root_dir)
    if config_file:
        properties = load_app_properties(
            config_file=os.path.abspath(config_file),
            config_section='galaxy',
        )
        if galaxy_root_dir:
            properties['root_dir'] = galaxy_root_dir
        return properties


@lru_cache(maxsize=1)
def get_config():
    kwargs = get_app_properties()
    if kwargs:
        kwargs['override_tempdir'] = False
        return Configuration(**kwargs)


def get_broker():
    config = get_config()
    if config:
        return config.amqp_internal_connection


def get_history_audit_table_prune_interval():
    config = get_config()
    if config:
        return config.history_audit_table_prune_interval
    else:
        return 3600


broker = get_broker()
celery_app = Celery('galaxy', broker=broker, include=['galaxy.celery.tasks'])
prune_interval = get_history_audit_table_prune_interval()
if prune_interval > 0:
    celery_app.conf.beat_schedule = {
        'prune-history-audit-table': {
            'task': 'galaxy.celery.tasks.prune_history_audit_table',
            'schedule': prune_interval,
        },
    }
celery_app.conf.timezone = 'UTC'


if __name__ == '__main__':
    celery_app.start()
