from lagom import magic_bind_to_container
from sqlalchemy.orm.scoping import (
    scoped_session,
)

from galaxy.celery import celery_app
from galaxy.managers.hdas import HDAManager
from galaxy.model import User
from galaxy.util.custom_logging import get_logger
from . import get_galaxy_app

log = get_logger(__name__)


def galaxy_task(func):
    app = get_galaxy_app()
    if app:
        return magic_bind_to_container(app)(func)
    return func


@celery_app.task
@galaxy_task
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


@celery_app.task
@galaxy_task
def purge_hda(hda_manager: HDAManager, hda_id):
    hda = hda_manager.by_id(hda_id)
    hda_manager._purge(hda)
