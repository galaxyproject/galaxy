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
    """
    If the target database is 'tool_shed', delegate to sqlalchemy migrate.
    Otherwise, handle with Alembic.
    """
    if sys.argv[-1] == "tool_shed":
        _run_sqlalchemy_migrate_on_toolshed()
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


def _run_sqlalchemy_migrate_on_toolshed():
    # This is the only case when we use SQLAlchemy Migrate.
    # This intentionally duplicates the code in `migrate_toolshed_db.py`.
    # The dependency on `migrate` should be removed prior to the move to SQLAlchemy 2.0.
    from migrate.versioning.shell import main

    from galaxy.model.orm.scripts import get_config

    config = get_config(sys.argv, use_argparse=False, cwd=os.getcwd())
    db_url = config["db_url"]
    repo = config["repo"]

    main(repository=repo, url=db_url)


if __name__ == "__main__":
    run()
