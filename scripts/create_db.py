"""
This script retrieves relevant configuration values and verifies the state of
the Galaxy and Tool Shed Install database(s).
There may be one combined database (galaxy and tool shed install) or two
separate databases.
If the database does not exist or is empty, it will be created and initialized.
(See inline comments in lib/galaxy/model/migrations/__init__.py for details on
how other database states are handled).
It is wrapped by create_db.sh (see that file for usage).
"""
import logging
import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.migrations import verify_databases_via_script
from galaxy.model.migrations.scripts import get_configuration

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def invoke_create():
    gxy_config, tsi_config, is_auto_migrate = get_configuration(sys.argv, os.getcwd())
    verify_databases_via_script(gxy_config, tsi_config, is_auto_migrate)


if __name__ == "__main__":
    invoke_create()
