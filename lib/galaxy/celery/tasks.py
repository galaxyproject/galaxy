import sys

from galaxy.celery import celery_app
from galaxy.datatypes.registry import Registry
from galaxy.model import (set_datatypes_registry, User)
from galaxy.model.mapping import init
from galaxy.model.orm.scripts import get_config
from galaxy.util.custom_logging import get_logger

log = get_logger(__name__)


def get_galaxy_context():
    # This insanity is because get_config (I think) is not cooperating with celery arg handling
    _preserved_argv = list(sys.argv[1:])
    del sys.argv[1:]

    registry = Registry()
    registry.load_datatypes()
    set_datatypes_registry(registry)
    db_url = get_config(sys.argv)['db_url']
    sa_session = init('/tmp/', db_url).context

    # Put the args back
    sys.argv.extend(_preserved_argv)
    return sa_session


@celery_app.task
def recalculate_user_disk_usage(user_id=None):
    sa_session = get_galaxy_context()
    if user_id:
        user = sa_session.query(User).get(user_id)
        if user:
            user.calculate_and_set_disk_usage()
            log.info(f"New user disk usage is {user.disk_usage}")
        else:
            log.error("Recalculate user disk usage task failed, user %s not found" % user_id)
    else:
        log.error("Recalculate user disk usage task received without user_id.")
