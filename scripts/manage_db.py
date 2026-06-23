"""
This script should not be used directly. It is intended to be used by the
ansible galaxy and toolshed roles.  For managing the database, please consult
manage_db.sh.
"""

import logging
import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))
from galaxy.model.migrations.scripts import LegacyManageDb

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def run():
    if sys.argv[-1] == "tool_shed":
        raise Exception(
            "Please use the `manage_toolshed_db.sh` script (or `scripts/toolshed_db.py` if running Ansible)."
        )
    else:
        arg = _get_command_argument()
        lmdb = LegacyManageDb()
        if arg == "version":
            result = lmdb.get_gxy_version()
        elif arg == "db_version":
            result = lmdb.get_gxy_db_version()
        else:
            result = lmdb.run_upgrade()
        if result:
            print(result)


def _get_command_argument():
    """
    If last argument is a valid command, pop and return it; otherwise raise exception.
    """
    arg = sys.argv[-1]
    if arg in ["version", "db_version", "upgrade"]:
        return arg
    else:
        raise Exception("Invalid command argument; should be: 'version', 'db_version', or 'upgrade'")


if __name__ == "__main__":
    run()
