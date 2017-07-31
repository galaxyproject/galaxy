from __future__ import print_function

import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.config import (
    configure_logging,
    find_path,
    find_root,
    parse_dependency_options,
)
from galaxy.script import main_factory


DESCRIPTION = "Script to determine uWSGI command line arguments."
COMMAND_TEMPLATE = '{virtualenv}--ini-paste {galaxy_ini}{mule}{farm}'


def _get_uwsgi_args(args, kwargs):
    handlerct = int(kwargs.get('job_handler_count', 1))
    pool_name = kwargs.get('job_handler_pool_name', 'job-handlers')
    virtualenv = os.environ.get('VIRTUAL_ENV', None)
    print(COMMAND_TEMPLATE.format(
        virtualenv='--virtualenv %s ' % virtualenv if virtualenv else '',
        galaxy_ini=args.config_file or kwargs['__file__'],
        mule=' --py-call-osafterfork' + ' --mule=lib/galaxy/main.py' * handlerct if handlerct else '',
        farm=' --farm=%s:%s' % (pool_name, ','.join([str(x) for x in range(1, handlerct + 1)]))))


ACTIONS = {
    "get_uwsgi_args": _get_uwsgi_args,
}


if __name__ == '__main__':
    main = main_factory(description=DESCRIPTION, actions=ACTIONS, default_action="get_uwsgi_args")
    main()
