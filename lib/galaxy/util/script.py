"""Utilities for Galaxy scripts
"""

import argparse
import logging
import os
import sys

from galaxy.util.properties import (
    find_config_file,
    load_app_properties,
)

DESCRIPTION = None
ACTIONS = None
ARGUMENTS = None
DEFAULT_ACTION = None

ARG_HELP_CONFIG_FILE = """
Galaxy config file (defaults to $GALAXY_ROOT/config/galaxy.yml if that file exists
or else to ./config/galaxy.ini if that exists). If this isn't set on the
command line it can be set with the environment variable GALAXY_CONFIG_FILE.
"""

# ARG_HELP_CONFIG_SECTION = """
# Section containing application configuration in the target config file specified with
# -c/--config-file. This defaults to 'galaxy' for YAML/JSON configuration files and 'main'
# with 'app:' prepended for INI. If this isn't set on the command line it can be set with
# the environment variable GALAXY_CONFIG_SECTION.
# """


def main_factory(description=None, actions=None, arguments=None, default_action=None):
    global DESCRIPTION, ACTIONS, ARGUMENTS, DEFAULT_ACTION
    DESCRIPTION = description
    ACTIONS = actions or {}
    ARGUMENTS = arguments or []
    DEFAULT_ACTION = default_action
    return main


def main(argv=None):
    """Entry point for conversion process."""
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)
    kwargs = app_properties_from_args(args)
    action = args.action
    action_func = ACTIONS[action]
    action_func(args, kwargs)


def app_properties_from_args(args, legacy_config_override=None, app=None):
    config_file = config_file_from_args(args, legacy_config_override=legacy_config_override, app=app)
    config_section = getattr(args, "config_section", None)
    app_properties = load_app_properties(config_file=config_file, config_section=config_section)
    return app_properties


def config_file_from_args(args, legacy_config_override=None, app=None):
    app = app or getattr(args, "app", "galaxy")
    config_file = legacy_config_override or args.config_file or find_config_file(app)
    return config_file


def populate_config_args(parser):
    # config and config-file respected because we have used different arguments at different
    # time for scripts.

    # Options (e.g. option_name) not found in this file can have their defaults overridden
    # set setting GALAXY_CONFIG_OPTION_NAME where OPTION_NAME is option_name converted to upper case.
    # Options specified in that file can be overridden for this program set setting
    # GALAXY_CONFIG_OVERRIDE_OPTION_NAME to a new value.
    parser.add_argument(
        "-c", "--config-file", "--config", default=os.environ.get("GALAXY_CONFIG_FILE", None), help=ARG_HELP_CONFIG_FILE
    )
    parser.add_argument(
        "--config-section", default=os.environ.get("GALAXY_CONFIG_SECTION", None), help=argparse.SUPPRESS
    )  # See ARG_HELP_CONFIG_SECTION comment above for unsuppressed details.


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "action",
        metavar="ACTION",
        type=str,
        choices=list(ACTIONS.keys()),
        default=DEFAULT_ACTION,
        nargs="?" if DEFAULT_ACTION is not None else None,
        help="action to perform",
    )
    populate_config_args(parser)
    parser.add_argument("--app", default=os.environ.get("GALAXY_APP", "galaxy"))
    for argument in ARGUMENTS:
        parser.add_argument(*argument[0], **argument[1])
    return parser


def set_log_handler(filename=None, stream=None):
    if filename:
        handler = logging.FileHandler(filename)
    else:
        handler = logging.StreamHandler(stream=stream)
    return handler
