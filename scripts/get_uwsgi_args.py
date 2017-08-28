from __future__ import print_function

import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.script import main_factory
from galaxy.util.properties import nice_config_parser


DESCRIPTION = "Script to determine uWSGI command line arguments."
COMMAND_TEMPLATE = '{virtualenv} --ini-paste {config_file}{processes}{threads}{http}{pythonpath}{master}{static-map}{paste-logger}{die-on-term}{enable-threads}{py-call-osafterfork}{mule}{farm}'


def _get_uwsgi_args(args, kwargs):
    config_file = args.config_file or kwargs['__file__']
    handlerct = int(kwargs.get('job_handler_count', 1))
    config = nice_config_parser(config_file)
    config_defaults = {
        'virtualenv': ' --virtualenv {venv}'.format(venv=os.environ.get('VIRTUAL_ENV', './.venv')),
        'processes': ' --processes 1',
        'threads': ' --threads 4',
        'http': ' --http localhost:8080',
        'pythonpath': ' --pythonpath lib',
        'master': ' --master',
        'static-map': (' --static-map /static/style={here}/static/style/blue'
                       ' --static-map /static={here}/static'.format(here=os.getcwd())),
        'paste-logger': ' --paste-logger' if config.has_section('formatters') else '',
        'die-on-term': ' --die-on-term',
        'enable-threads': ' --enable-threads',
        'py-call-osafterfork': ' --py-call-osafterfork',
        'mule': ' --mule=lib/galaxy/main.py' * handlerct,
        'farm': ' --farm={name}:{mules}'.format(
            name=kwargs.get('job_handler_pool_name', 'job-handlers'),
            mules=','.join([str(x) for x in range(1, handlerct + 1)])),
    }
    if not config.has_section('uwsgi'):
        format_dict = config_defaults
    else:
        format_dict = {}
        for opt in config_defaults.keys():
            if config.has_option('uwsgi', opt):
                format_dict[opt] = ''
            else:
                format_dict[opt] = config_defaults[opt]
    format_dict['config_file'] = config_file
    print(COMMAND_TEMPLATE.format(**format_dict))


ACTIONS = {
    "get_uwsgi_args": _get_uwsgi_args,
}


if __name__ == '__main__':
    main = main_factory(description=DESCRIPTION, actions=ACTIONS, default_action="get_uwsgi_args")
    main()
