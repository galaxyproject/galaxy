import os
from celery import Celery

from galaxy.util.custom_logging import get_logger

log = get_logger(__name__)

# This is a complete hack for now, todo: configure celery dynamically with the same galaxy internal amqp stuff.
celery_app = Celery('galaxy', broker="redis://localhost", include=['galaxy.celery.tasks'])


if __name__ == '__main__':
    import galaxy.app
    config_file = os.path.abspath(os.environ["GALAXY_CONFIG_FILE"])
    galaxy_app = galaxy.app.UniverseApplication(config_file=config_file)
    galaxy.app.app = galaxy_app
    celery_app.conf.update(broker=galaxy_app.config.amqp_internal_connection)
    celery_app.start()
