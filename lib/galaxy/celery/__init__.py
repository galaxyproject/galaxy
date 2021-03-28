import os
from functools import lru_cache

from celery import Celery

from galaxy.config import Configuration
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
    if config_file:
        return load_app_properties(
            config_file=os.path.abspath(config_file),
            config_section='galaxy',
        )


@lru_cache(maxsize=1)
def get_config():
    kwargs = get_app_properties()
    if kwargs:
        return Configuration(**kwargs)


def get_broker():
    config = get_config()
    if config:
        return config.amqp_internal_connection


broker = get_broker()
celery_app = Celery('galaxy', broker=broker, include=['galaxy.celery.tasks'])


if __name__ == '__main__':
    celery_app.start()
