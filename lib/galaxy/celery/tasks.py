from lagom import magic_bind_to_container
from sqlalchemy.orm.scoping import (
    scoped_session,
)

from galaxy.celery import celery_app
from galaxy.model import User
from galaxy.util.custom_logging import get_logger
from . import get_galaxy_app

log = get_logger(__name__)


def get_galaxy_context():
    app = get_galaxy_app()
    return app


@celery_app.task
@magic_bind_to_container(get_galaxy_context())
def recalculate_user_disk_usage(session: scoped_session, user_id=None):
    if user_id:
        user = session.query(User).get(user_id)
        if user:
            user.calculate_and_set_disk_usage()
            log.info(f"New user disk usage is {user.disk_usage}")
        else:
            log.error("Recalculate user disk usage task failed, user %s not found" % user_id)
    else:
        log.error("Recalculate user disk usage task received without user_id.")
