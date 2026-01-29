#!/usr/bin/env python

"""
This script is intended to be invoked by the scripts/run_alembic.sh script.
"""

import logging
import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.migrations.scripts import (
    add_db_urls_to_command_arguments,
    get_configuration,
    invoke_alembic,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

ALEMBIC_CONFIG = "lib/galaxy/model/migrations/alembic.ini"


def run():
    sys.argv.insert(1, "--config")
    sys.argv.insert(2, ALEMBIC_CONFIG)
    gxy_config, tsi_config, _ = get_configuration(sys.argv, os.getcwd())
    add_db_urls_to_command_arguments(sys.argv, gxy_config.url, tsi_config.url)
    invoke_alembic()


if __name__ == "__main__":
    run()
