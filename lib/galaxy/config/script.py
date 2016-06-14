#!/usr/bin/env python
from __future__ import print_function

import os
import string
import sys
from argparse import ArgumentParser

try:
    import pip
except ImportError:
    pip = None


CONFIGURE_URL = "https://wiki.galaxyproject.org/Admin/Config/Performance/ProductionServer"

DESCRIPTION = "Initialize a directory with a minimal Galaxy config."
HELP_CONFIG_DIR = "Directory containing the configuration files for Galaxy."
HELP_DATA_DIR = "Directory containing Galaxy-created data."
HELP_FORCE = "Overwrite existing files if they already exist."
HELP_WSGI_SERVER = ("Web server stack used to host Galaxy web application, and "
                    "if uWSGI, which protocol to use.")
HELP_LIBDRMAA = ("Configure Galaxy to submit jobs to a cluster via DRMAA by "
                 "supplying the path to a libdrmaa.so file using this argument.")
HELP_INSTALL = ("Install optional dependencies required by specified configuration "
                "(e.g. drmaa, uwsgi, etc...).")
HELP_HOST = ('Host to bind Galaxy to - defaults to localhost. Specify an IP '
             'address or "all" to listen on all interfaces.')
HELP_PORT = ("Port to bind Galaxy to.")

DEFAULT_HOST = "localhost"
DEFAULT_INI = "galaxy.ini"

SAMPLES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sample'))
GALAXY_CONFIG_TEMPLATE_FILE = os.path.join(SAMPLES_PATH, 'galaxy.ini.sample')

# The sample is used as the default config file for Galaxy started without a
# config, and we don't want to duplicate the whole thing into galaxy.config for
# templating, so for now just substitute some lines. In the future we will
# build configs differently.
GALAXY_CONFIG_SUBSTITUTIONS = {
    '#port = 8080': 'port = ${port}',
    '#host = 127.0.0.1': 'host = ${host}',
    'http = 127.0.0.1:8080': '${uwsgi_transport} = ${host}:${port}',
    '#config_dir = None': 'config_dir = ${config_dir}',
    '#data_dir = None': 'data_dir = ${data_dir}',
}


def main(argv=None):
    dependencies = []
    arg_parser = ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--config-dir",
                            default=".",
                            help=HELP_CONFIG_DIR)
    arg_parser.add_argument("--data-dir",
                            default="./data",
                            help=HELP_DATA_DIR)
    arg_parser.add_argument("--wsgi-server",
                            choices=["paster", "uwsgi-http", "uwsgi-native"],
                            default="paster",
                            help=HELP_WSGI_SERVER)
    arg_parser.add_argument("--host",
                            default=DEFAULT_HOST,
                            help=HELP_HOST)
    arg_parser.add_argument("--port",
                            default="8080",
                            help=HELP_PORT)
    arg_parser.add_argument("--install",
                            action="store_true",
                            help=HELP_INSTALL)
    arg_parser.add_argument("--force",
                            action="store_true",
                            default=False,
                            help=HELP_FORCE)
    args = arg_parser.parse_args(argv)
    config_dir = args.config_dir
    relative_config_dir = config_dir
    config_dir = os.path.abspath(config_dir)
    data_dir = args.data_dir
    relative_data_dir = data_dir
    data_dir = os.path.abspath(data_dir)

    mode = _determine_mode(args)
    if mode.startswith("uwsgi-"):
        dependencies.append("uwsgi")

    for directory in (config_dir, data_dir):
        if not os.path.exists(directory):
            os.makedirs(directory)

    print("Bootstrapping Galaxy configuration into directory %s" % relative_config_dir)
    _handle_galaxy_ini(args, config_dir, data_dir)
    _handle_install(args, dependencies)
    _print_config_summary(args, mode, relative_config_dir)


def _print_config_summary(args, mode, relative_config_dir):
    _print_galaxy_ini_info(args, mode)
    print("")
    print("For help on configuring Galaxy, consult the documentation at:\n ", CONFIGURE_URL)
    print("")
    print("Additional sample configuration files for various Galaxy components (jobs,")
    print("datatypes, etc.) can be found in:\n ", SAMPLES_PATH)
    print("")
    print("Start Galaxy by running the command from directory [%s]:" % relative_config_dir)
    _print_galaxy_run(mode)


def _print_galaxy_ini_info(args, mode):
    print(" - galaxy.ini created, update to configure Galaxy.")
    print("   * Target web server %s" % mode)
    if args.host == DEFAULT_HOST:
        print("   * Binding to host localhost, remote clients will not be able to connect.")
    elif _determine_host(args) == "0.0.0.0":
        print("   * Binding to all network interfaces.")
    else:
        print("   * Binding to host [%s].", args.host)


def _print_galaxy_run(mode):
    if mode.startswith("uwsgi"):
        print("    uwsgi --ini-paste galaxy.ini")
    else:
        print("    galaxy-paster serve galaxy.ini")


def _determine_mode(args):
    if args.wsgi_server:
        mode = args.wsgi_server
    else:
        mode = "paster"
    return mode


def _determine_host(args):
    return '0.0.0.0' if args.host == 'all' else args.host


def _determine_ini_file(config_dir):
    return os.path.join(config_dir, DEFAULT_INI)


def _handle_galaxy_ini(args, config_dir, data_dir):
    force = args.force
    ini_file = _determine_ini_file(config_dir)
    _check_file(ini_file, force)
    uwsgi_transport = 'socket' if args.wsgi_server == 'uwsgi-native' else 'http'
    config_dict = dict(
        port=args.port,
        host=_determine_host(args),
        uwsgi_transport=uwsgi_transport,
        config_dir=config_dir,
        data_dir=data_dir,
    )

    galaxy_config_template = []
    with open(GALAXY_CONFIG_TEMPLATE_FILE) as fh:
        for line in [ l.rstrip('\n') for l in fh.readlines() ]:
            for k, v in GALAXY_CONFIG_SUBSTITUTIONS.items():
                if line == k:
                    line = v
            galaxy_config_template.append(line)
    galaxy_config_template = string.Template('\n'.join(galaxy_config_template))

    galaxy_config = galaxy_config_template.safe_substitute(
        **config_dict
    )
    open(ini_file, "w").write(galaxy_config)


def _handle_install(args, dependencies):
    if args.install and dependencies:
        if pip is None:
            raise ImportError("Bootstrapping Pulsar dependencies requires pip library.")

        pip.main(["install"] + dependencies)


def _check_file(path, force):
    if os.path.exists(path) and not force:
        print("File %s exists, exiting. Run with --force to replace configuration." % path, file=sys.stderr)
        sys.exit(1)
