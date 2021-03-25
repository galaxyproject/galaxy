import os
from functools import lru_cache

from celery import Celery

from galaxy.config import Configuration
from galaxy.util.custom_logging import get_logger
from galaxy.util.properties import load_app_properties

log = get_logger(__name__)


@lru_cache
def get_galaxy_app():
    import galaxy.app
    if galaxy.app.app:
        return galaxy.app.app
    galaxy_app = galaxy.app.MinimalGalaxyApplication(configure_logging=False, **get_galaxy_config())
    return galaxy_app


def get_galaxy_config():
    config_file = os.path.abspath(os.environ.get("GALAXY_CONFIG_FILE"))
    return load_app_properties(
        config_file=config_file,
        config_section='galaxy',
    )


broker = Configuration(**get_galaxy_config()).amqp_internal_connection
celery_app = Celery('galaxy', broker=broker, include=['galaxy.celery.tasks'])
log.warning(f"BROKER IS {broker}")


if __name__ == '__main__':
    celery_app.start()
