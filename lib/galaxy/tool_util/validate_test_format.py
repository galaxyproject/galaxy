#!/usr/bin/env python

import argparse
import sys

import yaml

from galaxy.tool_util.models import Tests

DESCRIPTION = """
A small utility to verify the Planemo test format.

This script doesn't use semantic information about tools or workflows so only
the structure of the file is checked and things like inputs matching up is not
included.
"""


def validate_test_file(test_file: str) -> None:
    with open(test_file) as f:
        json = yaml.safe_load(f)
    Tests.model_validate(json)


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("test_file")
    return parser


def main(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = arg_parser().parse_args(argv)
    validate_test_file(args.test_file)


if __name__ == "__main__":
    main()
