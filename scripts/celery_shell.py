"""
Run this script from galaxy's root with
```
ipython -i scripts/celery_shell.py -- -c config/galaxy.yml
```
"""
import logging
import os

WARNING_MODULES = ["parso", "asyncio", "galaxy.datatypes"]
for mod in WARNING_MODULES:
    logger = logging.getLogger(mod)
    logger.setLevel("WARNING")

from scripts.db_shell import config

os.environ["GALAXY_CONFIG_FILE"] = os.environ.get("GALAXY_CONFIG_FILE", config["config_file"])

from galaxy.celery import tasks  # noqa: F401
from galaxy.celery import get_galaxy_app

HELP = """
============
Run celery tasks interactively.
tasks are collected in task module.

To run recalculate_user_disk_usage for user 1 in a celery worker
type
>>> tasks.recalculate_user_disk_usage.delay(user_id=1)
"""

app = get_galaxy_app()
print(HELP)
