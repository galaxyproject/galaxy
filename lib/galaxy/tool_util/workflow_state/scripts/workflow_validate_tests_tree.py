"""Thin CLI entry point for gxwf-validate-tests-tree."""

import argparse

from .._cli_common import (
    add_report_args,
    cli_main,
    cli_main_from_args,
)
from .._report_models import TestsTreeReport
from ..validate_tests import (
    run_validate_tests_tree,
    ValidateTestsTreeOptions,
)

SUBCOMMAND = "validate-tests-tree"


def _add_args(parser):
    parser.add_argument("--summary", action="store_true", help="Show only summary counts")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="No-op placeholder; test validation is already fully strict.",
    )
    add_report_args(parser)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gxwf-validate-tests-tree",
        description="Validate all workflow-tests YAML files under a directory tree.",
    )
    parser.add_argument("workflow_path", help="Path to a directory containing *-tests.yml files")
    _add_args(parser)
    return parser


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Validate all workflow-tests YAML files under a directory tree")
    p.add_argument("workflow_path", help="Path to a directory containing *-tests.yml files")
    _add_args(p)
    p.set_defaults(
        func=lambda args: cli_main_from_args(ValidateTestsTreeOptions, run_validate_tests_tree, args, TestsTreeReport)
    )


def main(argv=None):
    cli_main(
        build_parser(),
        ValidateTestsTreeOptions,
        run_validate_tests_tree,
        argv,
        report_schema_model=TestsTreeReport,
    )


if __name__ == "__main__":
    main()
