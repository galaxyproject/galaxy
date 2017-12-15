"""Utilities for Galaxy scripts
"""
import argparse
import os
import sys

from galaxy.util.properties import find_config_file, load_app_properties

DESCRIPTION = None
ACTIONS = None
ARGUMENTS = None
DEFAULT_ACTION = None


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
    kwargs = _app_properties(args)
    action = args.action
    action_func = ACTIONS[action]
    action_func(args, kwargs)


def _app_properties(args):
    # FIXME: you can use galaxy.util.path.extensions for this
    config_file = args.config_file or find_config_file(args.app)
    app_properties = load_app_properties(config_file=config_file, config_section=args.config_section)
    return app_properties


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('action', metavar='ACTION', type=str,
                        choices=list(ACTIONS.keys()),
                        default=DEFAULT_ACTION,
                        nargs='?' if DEFAULT_ACTION is not None else None,
                        help='action to perform')
    parser.add_argument("-c", "--config-file",
                        default=os.environ.get('GALAXY_CONFIG_FILE', None))
    parser.add_argument("--config-section",
                        default=os.environ.get('GALAXY_CONFIG_SECTION', None))
    parser.add_argument("--app",
                        default=os.environ.get('GALAXY_APP', 'galaxy'))
    for argument in ARGUMENTS:
        parser.add_argument(*argument[0], **argument[1])
    return parser
