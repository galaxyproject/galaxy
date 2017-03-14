"""Utilities for Galaxy scripts
"""
import argparse
import os
import sys

from galaxy.util.properties import find_config_file, load_app_properties

DESCRIPTION = None
ACTIONS = None
ARGUMENTS = None


def main_factory(description=None, actions=None, arguments=None):
    global DESCRIPTION, ACTIONS, ARGUMENTS
    DESCRIPTION = description
    ACTIONS = actions or {}
    ARGUMENTS = arguments or []
    return main


def main(argv=None):
    """Entry point for conversion process."""
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)
    kwargs = _app_properties(args)
    action = args.action
    action_func = ACTIONS[action]
    action_func(args, kwargs)


def _app_properties(args):
    config_file = find_config_file("config/galaxy.ini", "universe_wsgi.ini", args.config_file)
    app_properties = load_app_properties(ini_file=config_file)
    return app_properties


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('action', metavar='ACTION', type=str,
                        choices=ACTIONS.keys(),
                        help='action to perform')
    parser.add_argument("-c", "--config-file",
                        default=os.environ.get('GALAXY_CONFIG_FILE', None))
    for argument in ARGUMENTS:
        parser.add_argument(*argument[0], **argument[1])
    return parser
