from galaxy.celery import celery_app
from galaxy.util.custom_logging import get_logger
from . import get_galaxy_app

log = get_logger(__name__)


def get_galaxy_context():
    app = get_galaxy_app()
    return app


@celery_app.task
def recalculate_user_disk_usage(user_id=None):
    app = get_galaxy_context()
    sa_session = app.model.session
    if user_id:
        user = sa_session.query(app.model.User).get(user_id)
        if user:
            user.calculate_and_set_disk_usage()
            log.info(f"New user disk usage is {user.disk_usage}")
        else:
            log.error("Recalculate user disk usage task failed, user %s not found" % user_id)
    else:
        log.error("Recalculate user disk usage task received without user_id.")
