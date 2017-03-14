from __future__ import print_function

import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.config import (
    configure_logging,
    find_path,
    find_root,
    parse_dependency_options,
)
from galaxy.script import main_factory
from galaxy.tools.deps import CachedDependencyManager, DependencyManager, NullDependencyManager

DESCRIPTION = "Script to determine uWSGI command line arguments."


def _get_uwsgi_args(args, kwargs):
    print('--ini-paste {galaxy_ini}{mule}'.format(
        galaxy_ini=args.config_file,
        mule=' --mule=lib/galaxy/main.py' * int(kwargs.get('job_handler_count', 1))))


ACTIONS = {
    "get_uwsgi_args": _get_uwsgi_args,
}


if __name__ == '__main__':
    main = main_factory(description=DESCRIPTION, actions=ACTIONS)
    main()
