from galaxy.celery import celery_app, get_galaxy_app
from galaxy.util.custom_logging import get_logger

log = get_logger(__name__)


@celery_app.task
def recalculate_user_disk_usage(user_id=None):
    # This is not initializing like I want it to I don't think.
    app = get_galaxy_app()
    sa_session = app.model.context
    if user_id:
        user = sa_session.query(app.model.User).get(app.security.decode_id(user_id))
        if user:
            user.calculate_and_set_disk_usage()
        else:
            log.error("Recalculate user disk usage task failed, user %s not found" % user_id)
    else:
        log.error("Recalculate user disk usage task received without user_id.")
