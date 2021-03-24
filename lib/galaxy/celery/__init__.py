import os
from celery import Celery
from galaxy.util.properties import load_app_properties

from galaxy.util.custom_logging import get_logger

log = get_logger(__name__)

# This is a complete hack for now, todo: configure celery dynamically with the same galaxy internal amqp stuff.
celery_app = Celery('galaxy', broker="redis://localhost", include=['galaxy.celery.tasks'])


def get_galaxy_app():
    import galaxy.app
    if galaxy.app.app:
        return galaxy.app.app
    config_file = os.path.abspath(os.environ["GALAXY_CONFIG_FILE"])
    kwargs = load_app_properties(
        config_file=config_file,
        config_section='galaxy',
    )
    galaxy_app = galaxy.app.UniverseApplication(**kwargs)
    return galaxy_app


if __name__ == '__main__':
    #galaxy_app = get_galaxy_app()
    #celery_app.conf.update(broker=galaxy_app.config.amqp_internal_connection)
    celery_app.start()
