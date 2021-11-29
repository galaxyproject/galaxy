from scripts.db_shell import *

from galaxy.celery import get_galaxy_app

from galaxy.celery.tasks import *

app = get_galaxy_app()
assert app, 'Set GALAXY_CONFIG_FILE to the path of your galaxy.yml file'
