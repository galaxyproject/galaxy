#!/usr/bin/env python

import os
import string
import sys
from argparse import ArgumentParser

try:
    import pip
except ImportError:
    pip = None  # type: ignore[assignment]


CONFIGURE_URL = "https://docs.galaxyproject.org/en/master/admin/"

DESCRIPTION = "Initialize a directory with a minimal Galaxy config."
HELP_CONFIG_DIR = "Directory containing the configuration files for Galaxy."
HELP_DATA_DIR = "Directory containing Galaxy-created data."
HELP_FORCE = "Overwrite existing files if they already exist."
HELP_INSTALL = "Install optional dependencies required by specified configuration (e.g. drmaa, etc...)."
HELP_HOST = (
    'Host to bind Galaxy to - defaults to localhost. Specify an IP address or "all" to listen on all interfaces.'
)
HELP_PORT = "Port to bind Galaxy to."
HELP_DB_CONN = "Galaxy database connection URI."

DEFAULT_HOST = "localhost"
DEFAULT_YML = "galaxy.yml"
DEFAULT_DB_CONN = "sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE"

SAMPLES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample"))
GALAXY_CONFIG_TEMPLATE_FILE = os.path.join(SAMPLES_PATH, "galaxy.yml.sample")
STATIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "web", "framework", "static"))
CLIENT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "client"))

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
    "  #config_dir: false": "  config_dir: ${config_dir}",
    "  #data_dir: false": "  data_dir: ${data_dir}",
    "  #database_connection: sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE": "  database_connection: ${database_connection}",
}


def main(argv=None):
    dependencies = []
    arg_parser = ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--config-dir", default=".", help=HELP_CONFIG_DIR)
    arg_parser.add_argument("--data-dir", default="./data", help=HELP_DATA_DIR)
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

    print(f"Bootstrapping Galaxy configuration into directory {relative_config_dir}")
    _handle_galaxy_yml(args, config_dir, data_dir)
    _handle_install(args, dependencies)
    _print_config_summary(args, mode, relative_config_dir)


def _print_config_summary(args, mode, relative_config_dir):
    _print_galaxy_yml_info(args, mode)
    print(MSG_CONFIG_SUMMARY.format(CONFIGURE_URL, SAMPLES_PATH, relative_config_dir))


def _print_galaxy_yml_info(args, mode):
    print(" - galaxy.yml created, update to configure Galaxy.")
    print(f"   * Target web server {mode}")
    if args.host == DEFAULT_HOST:
        print("   * Binding to host localhost, remote clients will not be able to connect.")
    elif _determine_host(args) == "0.0.0.0":
        print("   * Binding to all network interfaces.")
    else:
        print("   * Binding to host [%s].", args.host)


def _determine_mode(args):
    return "gunicorn"


def _determine_host(args):
    return "0.0.0.0" if args.host == "all" else args.host


def _determine_yml_file(config_dir):
    return os.path.join(config_dir, DEFAULT_YML)


def _handle_galaxy_yml(args, config_dir, data_dir):
    force = args.force
    yml_file = _determine_yml_file(config_dir)
    _check_file(yml_file, force)
    config_dict = dict(
        port=args.port,
        host=_determine_host(args),
        config_dir=config_dir,
        data_dir=data_dir,
        client_dir=CLIENT_PATH,
        static_path=STATIC_PATH,
        database_connection=args.db_conn,
    )

    galaxy_config_template = []
    with open(GALAXY_CONFIG_TEMPLATE_FILE) as fh:
        for line in fh:
            line = line.rstrip("\n")
            for k, v in GALAXY_CONFIG_SUBSTITUTIONS.items():
                if line == k:
                    line = v
            galaxy_config_template.append(line)
    galaxy_config_template = string.Template("\n".join(galaxy_config_template))

    galaxy_config = galaxy_config_template.safe_substitute(**config_dict)
    open(yml_file, "w").write(galaxy_config)


def _handle_install(args, dependencies):
    if args.install and dependencies:
        if pip is None:
            raise ImportError("Bootstrapping Galaxy dependencies requires pip.")

        pip.main(["install"] + dependencies)


def _check_file(path, force):
    if os.path.exists(path) and not force:
        print(f"File {path} exists, exiting. Run with --force to replace configuration.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
