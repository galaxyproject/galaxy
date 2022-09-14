"""
This script parses the Tool Shed config file for database connection
and then delegates to sqlalchemy_migrate shell main function in
migrate.versioning.shell.
It is wrapped by manage_db.sh (see that file for usage).
"""
import logging
import os.path
import sys

from migrate.versioning.shell import main

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.orm.scripts import get_config

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def invoke_migrate_main():
    # Migrate has its own args, so cannot use argparse
    config = get_config(sys.argv, use_argparse=False, cwd=os.getcwd())
    db_url = config["db_url"]
    repo = config["repo"]

    main(repository=repo, url=db_url)


if __name__ == "__main__":
    invoke_migrate_main()
