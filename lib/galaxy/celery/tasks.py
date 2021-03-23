from galaxy.celery import app
from galaxy.util.custom_logging import get_logger

log = get_logger(__name__)


@app.task
def recalculate_user_disk_usage(user_id=None):
    sa_session = app.model.context  # TODO: not remotely correct; this needs the actual model from our webless application context.
    if user_id:
        user = sa_session.query(app.model.User).get(app.security.decode_id(user_id))
        if user:
            user.calculate_and_set_disk_usage()
        else:
            log.error("Recalculate user disk usage task failed, user %s not found" % user_id)
    else:
        log.error("Recalculate user disk usage task received without user_id.")
