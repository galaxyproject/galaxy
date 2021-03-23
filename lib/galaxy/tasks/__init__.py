from celery import Celery
from galaxy.util.custom_logging import get_logger
log = get_logger(__name__)

# Test redis server, TODO: import the real app and use the same broker from config.

app = Celery('tasks', broker='redis://localhost')


@app.task
def recalculate_user_disk_usage(user_id=None):
    sa_session = app.model.context
    if user_id:
        user = sa_session.query(app.model.User).get(app.security.decode_id(user_id))
        if user:
            user.calculate_and_set_disk_usage()
        else:
            log.error("Recalculate user disk usage task failed, user %s not found" % user_id)
    else:
        log.error("Recalculate user disk usage task received without user_id.")
