#!/usr/bin/env python

import errno
import os
import shlex
import sys
import warnings
from argparse import ArgumentParser
from subprocess import check_call

import galaxy.dependencies

DESCRIPTION = "Install optional Galaxy dependencies based on configuration values"
PINNED_REQUIREMENTS = os.path.join(os.path.dirname(__file__), "pinned-requirements.txt")

HELP_PINNED = (
    "Include pinned required dependencies in install command, ensures all dependencies are installed at "
    "expected versions for the Galaxy release"
)
HELP_INSTALL = "Perform install, if unset then only output what would have been performed"
HELP_FREEZE = "Instead of installing, output requirent format to stdout"
HELP_CONFIG_FILE = "Path to Galaxy config file (galaxy.yml)"

# Warnings raised by dependency imports
warnings.filterwarnings("ignore")


def main(argv=None):
    dependencies = []
    arg_parser = ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--pinned", action="store_true", help=HELP_PINNED)
    arg_parser.add_argument("--install", action="store_true", help=HELP_INSTALL)
    arg_parser.add_argument("--freeze", action="store_true", help=HELP_FREEZE)
    arg_parser.add_argument("--config_file", "-c", help=HELP_CONFIG_FILE)
    args = arg_parser.parse_args(argv)
    config_file = args.config_file
    if config_file and not os.path.exists(config_file):
        print(f"{arg_parser.prog}: {config_file}: {os.strerror(errno.ENOENT)}", file=sys.stderr)
        sys.exit(1)
    dependencies = galaxy.dependencies.optional(config_file)
    if args.freeze:
        _handle_freeze(args, dependencies)
    elif dependencies or args.pinned:
        _handle_install(args, dependencies)
    else:
        print("Nothing to install", file=sys.stderr)


def _handle_freeze(args, dependencies):
    print("# generated with galaxy-dependencies")
    if args.pinned:
        print(f"-r {PINNED_REQUIREMENTS}")
    print("\n".join(dependencies))


def _handle_install(args, dependencies):
    req_file = []
    if args.pinned:
        req_file = ["-r", PINNED_REQUIREMENTS]
    cmd = [sys.executable, "-m", "pip", "install"] + req_file + dependencies
    print("Installing dependencies with:", file=sys.stderr)
    print(f"> {shlex.join(cmd)}", file=sys.stderr)
    if args.install:
        check_call(cmd)
    else:
        print("Dry run, use --install to perform installation", file=sys.stderr)


if __name__ == "__main__":
    main()
