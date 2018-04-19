""" This script parses Galaxy or Tool Shed config file for database connection
and then delegates to sqlalchemy_migrate shell main function in
migrate.versioning.shell. """
import os.path
import sys

from migrate.versioning.shell import main

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.model.orm.scripts import get_config


def invoke_migrate_main():
    # Migrate has its own args, so cannot use argparse
    config = get_config(sys.argv, use_argparse=False)
    db_url = config['db_url']
    repo = config['repo']

    main(repository=repo, url=db_url)


if __name__ == "__main__":
    invoke_migrate_main()
