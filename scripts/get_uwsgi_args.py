from __future__ import print_function

import os
import sys

from six import string_types
from six.moves import shlex_quote

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.util.path import get_ext
from galaxy.util.properties import load_app_properties, nice_config_parser
from galaxy.util.script import main_factory


DESCRIPTION = "Script to determine uWSGI command line arguments"
# socket is not an alias for http, but it is assumed that if you configure a socket in your uwsgi config you do not
# want to run the default http server (or you can configure it yourself)
ALIASES = {
    'virtualenv': ('home', 'venv', 'pyhome'),
    'pythonpath': ('python-path', 'pp'),
    'http': ('httprouter', 'socket', 'uwsgi-socket', 'suwsgi-socket', 'ssl-socket'),
    'module': ('mount',),   # mount is not actually an alias for module, but we don't want to set module if mount is set
}
DEFAULT_ARGS = {
    '_all_': ('pythonpath', 'threads', 'buffer-size', 'http', 'static-map', 'static-safe', 'die-on-term', 'hook-master-start', 'enable-threads'),
    'galaxy': ('py-call-osafterfork',),
    'reports': (),
    'tool_shed': (),
}
DEFAULT_PORTS = {
    'galaxy': 8080,
    'reports': 9001,
    'tool_shed': 9009,
}


def __arg_set(arg, kwargs):
    if arg in kwargs:
        return True
    for alias in ALIASES.get(arg, ()):
        if alias in kwargs:
            return True
    return False


def __add_arg(args, arg, value):
    optarg = '--%s' % arg
    if isinstance(value, bool):
        if value is True:
            args.append(optarg)
    elif isinstance(value, string_types):
        # the = in --optarg=value is usually, but not always, optional
        if value.startswith('='):
            args.append(shlex_quote(optarg + value))
        else:
            args.append(optarg)
            args.append(shlex_quote(value))
    else:
        [__add_arg(args, arg, v) for v in value]


def __add_config_file_arg(args, config_file, app):
    ext = None
    if config_file:
        ext = get_ext(config_file)
    if ext in ('yaml', 'json'):
        __add_arg(args, ext, config_file)
    elif ext == 'ini':
        config = nice_config_parser(config_file)
        has_logging = config.has_section('loggers')
        if config.has_section('app:main'):
            # uWSGI does not have any way to set the app name when loading with paste.deploy:loadapp(), so hardcoding
            # the name to `main` is fine
            __add_arg(args, 'ini-paste' if not has_logging else 'ini-paste-logged', config_file)
            return  # do not add --module
        else:
            __add_arg(args, ext, config_file)
            if has_logging:
                __add_arg(args, 'paste-logger', True)


def _get_uwsgi_args(cliargs, kwargs):
    # it'd be nice if we didn't have to reparse here but we need things out of more than one section
    config_file = cliargs.config_file or kwargs.get('__file__')
    uwsgi_kwargs = load_app_properties(config_file=config_file, config_section='uwsgi')
    args = []
    defaults = {
        'pythonpath': 'lib',
        'threads': '4',
        'buffer-size': '16384',  # https://github.com/galaxyproject/galaxy/issues/1530
        'http': 'localhost:{port}'.format(port=DEFAULT_PORTS[cliargs.app]),
        'static-map': ('/static/style={here}/static/style/blue'.format(here=os.getcwd()),
                       '/static={here}/static'.format(here=os.getcwd()),
                       '/favicon.ico={here}/static/favicon.ico'.format(here=os.getcwd())),
        'static-safe': ('{here}/config/plugins/visualizations'.format(here=os.getcwd()),
                        '{here}/client/galaxy/images'.format(here=os.getcwd()),
                        '{here}/config/plugins/interactive_environments'.format(here=os.getcwd())),
        'die-on-term': True,
        'enable-threads': True,
        'hook-master-start': ('unix_signal:2 gracefully_kill_them_all',
                              'unix_signal:15 gracefully_kill_them_all'),
        'py-call-osafterfork': True,
    }
    __add_config_file_arg(args, config_file, cliargs.app)
    if not __arg_set('module', uwsgi_kwargs):
        __add_arg(args, 'module', 'galaxy.webapps.{app}.buildapp:uwsgi_app()'.format(app=cliargs.app))
    # only include virtualenv if it's set/exists, otherwise this breaks conda-env'd Galaxy
    if not __arg_set('virtualenv', uwsgi_kwargs) and ('VIRTUAL_ENV' in os.environ or os.path.exists('.venv')):
        __add_arg(args, 'virtualenv', os.environ.get('VIRTUAL_ENV', '.venv'))
    for arg in DEFAULT_ARGS['_all_'] + DEFAULT_ARGS[cliargs.app]:
        if not __arg_set(arg, uwsgi_kwargs):
            __add_arg(args, arg, defaults[arg])
    print(' '.join(args))


ACTIONS = {
    "get_uwsgi_args": _get_uwsgi_args,
}


if __name__ == '__main__':
    main = main_factory(description=DESCRIPTION, actions=ACTIONS, default_action="get_uwsgi_args")
    main()
