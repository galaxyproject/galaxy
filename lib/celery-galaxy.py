"""Standlone entry point for starting a Celery worker that can execute Galaxy tasks"""
from galaxy.queue_worker import get_celery_app


# TODO: figure out how to build Galaxy app object using celery command line options
app = get_celery_app(None)
