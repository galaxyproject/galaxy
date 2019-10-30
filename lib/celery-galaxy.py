"""Standlone entry point for starting a Celery worker that can execute Galaxy tasks"""
import os
import sys

from celery import bootsteps
from celery.bin import Option

from galaxy.app import UniverseApplication
from galaxy.queue_worker import get_celery_app
from galaxy.util.properties import load_app_properties
from galaxy.web_stack import get_app_kwds

GALAXY_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
if not os.path.exists(os.path.join(GALAXY_ROOT_DIR, 'run.sh')):
    # Galaxy is installed
    GALAXY_ROOT_DIR = None
else:
    GALAXY_LIB_DIR = os.path.join(GALAXY_ROOT_DIR, "lib")
    try:
        sys.path.insert(1, GALAXY_LIB_DIR)
    except Exception:
        sys.exit("Failed to add Galaxy to sys.path")

# TODO: figure out how to build Galaxy app object using celery command line options
app = get_celery_app(None)
app.user_options['worker'].add(
    Option(
        '--galaxy_config_file',
        dest='galaxy_config_file',
        default='../config/galaxy.yml',
        type=str,
        help='Path to galaxy config file',
    )
)


class GalaxyWorkerStep(bootsteps.StartStopStep):
    requires = {'celery.worker.components:Pool'}

    def __init__(self, worker, galaxy_config_file=None, **options):
        app.conf['galaxy_config_file'] = galaxy_config_file = galaxy_config_file[0] if isinstance(galaxy_config_file, list) else galaxy_config_file
        kwds = get_app_kwds('galaxy')
        kwds = load_app_properties(config_file=galaxy_config_file, **kwds)
        kwds['config_file'] = galaxy_config_file
        kwds['root_dir'] = GALAXY_ROOT_DIR
        print(kwds)
        app.conf['galaxy_app'] = UniverseApplication(**kwds)


app.steps['worker'].add(GalaxyWorkerStep)
