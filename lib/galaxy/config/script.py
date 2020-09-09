#!/usr/bin/env python

import os
import string
import sys
from argparse import ArgumentParser

try:
    import pip
except ImportError:
    pip = None


CONFIGURE_URL = "https://docs.galaxyproject.org/en/master/admin/"

DESCRIPTION = "Initialize a directory with a minimal Galaxy config."
HELP_CONFIG_DIR = "Directory containing the configuration files for Galaxy."
HELP_DATA_DIR = "Directory containing Galaxy-created data."
HELP_FORCE = "Overwrite existing files if they already exist."
HELP_WSGI_SERVER = ("Web server stack used to host Galaxy web application, and if uWSGI, which protocol to use.")
HELP_LIBDRMAA = (
    "Configure Galaxy to submit jobs to a cluster via DRMAA by supplying the path to a libdrmaa.so file using this "
    "argument."
)
HELP_INSTALL = ("Install optional dependencies required by specified configuration (e.g. drmaa, etc...).")
HELP_HOST = (
    'Host to bind Galaxy to - defaults to localhost. Specify an IP address or "all" to listen on all interfaces.'
)
HELP_PORT = ("Port to bind Galaxy to.")
HELP_DB_CONN = ("Galaxy database connection URI.")

DEFAULT_HOST = "localhost"
DEFAULT_YML = "galaxy.yml"
DEFAULT_DB_CONN = 'sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE'

SAMPLES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sample'))
GALAXY_CONFIG_TEMPLATE_FILE = os.path.join(SAMPLES_PATH, 'galaxy.yml.sample')
STATIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'web', 'framework', 'static'))
CLIENT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'client'))

MSG_CONFIG_SUMMARY = """
For help on configuring Galaxy, consult the documentation at: \n {}

Additional sample configuration files for various Galaxy components (jobs,
datatypes, etc.) can be found in:\n {}

Start Galaxy by running the command from directory [{}]:
"""

# The sample is used as the default config file for Galaxy started without a config, and we don't want to duplicate the
# whole thing into galaxy.config for templating, so for now just substitute some lines. In the future we will build
# configs differently.
GALAXY_CONFIG_SUBSTITUTIONS = {
    '  http: 127.0.0.1:8080': '  ${uwsgi_transport}: ${host}:${port}',
    '  static-map: /static=static': '  static-map: /static=${static_path}',
    '  static-map: /favicon.ico=static/favicon.ico': '  static-map: /static=${static_path}/favicon.ico',
    '  static-safe: client/src/assets': '  ${client_path}/src/assets',
    '  virtualenv: .venv': '  #venv: .venv   # not used when running installed',
    '  pythonpath: lib': '  #pythonpath: lib  # not used  when running installed',
    '  #config_dir: false': '  config_dir: ${config_dir}',
    '  #data_dir: false': '  data_dir: ${data_dir}',
    '  #database_connection: sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE': '  database_connection: ${database_connection}',
}


def main(argv=None):
    dependencies = []
    arg_parser = ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--config-dir", default=".", help=HELP_CONFIG_DIR)
    arg_parser.add_argument("--data-dir", default="./data", help=HELP_DATA_DIR)
    arg_parser.add_argument("--wsgi-server", choices=["uwsgi-http", "uwsgi-native"], default="uwsgi-http",
                            help=HELP_WSGI_SERVER)
    arg_parser.add_argument("--host", default=DEFAULT_HOST, help=HELP_HOST)
    arg_parser.add_argument("--port", default="8080", help=HELP_PORT)
    arg_parser.add_argument("--db-conn", default=DEFAULT_DB_CONN, help=HELP_DB_CONN)
    arg_parser.add_argument("--install", action="store_true", help=HELP_INSTALL)
    arg_parser.add_argument("--force", action="store_true", default=False, help=HELP_FORCE)
    args = arg_parser.parse_args(argv)
    config_dir = args.config_dir
    relative_config_dir = config_dir
    config_dir = os.path.abspath(config_dir)
    data_dir = args.data_dir
    data_dir = os.path.abspath(data_dir)

    mode = _determine_mode(args)
    if args.db_conn.startswith("postgresql://"):
        dependencies.append("psycopg2-binary")

    for directory in (config_dir, data_dir):
        if not os.path.exists(directory):
            os.makedirs(directory)

    print("Bootstrapping Galaxy configuration into directory %s" % relative_config_dir)
    _handle_galaxy_yml(args, config_dir, data_dir)
    _handle_install(args, dependencies)
    _print_config_summary(args, mode, relative_config_dir)


def _print_config_summary(args, mode, relative_config_dir):
    _print_galaxy_yml_info(args, mode)
    print(MSG_CONFIG_SUMMARY.format(CONFIGURE_URL, SAMPLES_PATH, relative_config_dir))
    _print_galaxy_run(mode)


def _print_galaxy_yml_info(args, mode):
    print(" - galaxy.yml created, update to configure Galaxy.")
    print("   * Target web server %s" % mode)
    if args.host == DEFAULT_HOST:
        print("   * Binding to host localhost, remote clients will not be able to connect.")
    elif _determine_host(args) == "0.0.0.0":
        print("   * Binding to all network interfaces.")
    else:
        print("   * Binding to host [%s].", args.host)


def _print_galaxy_run(mode):
    if mode.startswith("uwsgi"):
        print("    uwsgi --yaml galaxy.yml")
    else:
        raise Exception("Unknown mode: %s" % mode)


def _determine_mode(args):
    if args.wsgi_server:
        mode = args.wsgi_server
    else:
        mode = "paster"
    return mode


def _determine_host(args):
    return '0.0.0.0' if args.host == 'all' else args.host


def _determine_yml_file(config_dir):
    return os.path.join(config_dir, DEFAULT_YML)


def _handle_galaxy_yml(args, config_dir, data_dir):
    force = args.force
    yml_file = _determine_yml_file(config_dir)
    _check_file(yml_file, force)
    uwsgi_transport = 'socket' if args.wsgi_server == 'uwsgi-native' else 'http'
    config_dict = dict(
        port=args.port,
        host=_determine_host(args),
        uwsgi_transport=uwsgi_transport,
        config_dir=config_dir,
        data_dir=data_dir,
        client_dir=CLIENT_PATH,
        static_path=STATIC_PATH,
        database_connection=args.db_conn,
    )

    galaxy_config_template = []
    with open(GALAXY_CONFIG_TEMPLATE_FILE) as fh:
        for line in [l.rstrip('\n') for l in fh.readlines()]:
            for k, v in GALAXY_CONFIG_SUBSTITUTIONS.items():
                if line == k:
                    line = v
            galaxy_config_template.append(line)
    galaxy_config_template = string.Template('\n'.join(galaxy_config_template))

    galaxy_config = galaxy_config_template.safe_substitute(
        **config_dict
    )
    open(yml_file, "w").write(galaxy_config)


def _handle_install(args, dependencies):
    if args.install and dependencies:
        if pip is None:
            raise ImportError("Bootstrapping Galaxy dependencies requires pip.")

        pip.main(["install"] + dependencies)


def _check_file(path, force):
    if os.path.exists(path) and not force:
        print("File %s exists, exiting. Run with --force to replace configuration." % path, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
