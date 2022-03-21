"""
Creates the initial tool shed database schema using the settings defined in config/tool_shed.yml.

Note: pass '-c /location/to/your_config.yml' for non-standard ini file locations.

Note: if no database_connection is set in tool_shed.yml, the default, sqlite database will be constructed.

This script is also wrapped by create_ts_db.sh.
"""
import logging
import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.orm.scripts import get_config
from tool_shed.webapp.model.migrate.check import create_or_verify_database as create_tool_shed_db

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def invoke_create():
    config = get_config(sys.argv)
    create_tool_shed_db(config["db_url"])


if __name__ == "__main__":
    invoke_create()
