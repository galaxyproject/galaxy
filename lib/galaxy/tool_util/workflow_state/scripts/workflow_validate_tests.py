"""Thin CLI entry point for gxwf-validate-tests."""

import argparse

from .._cli_common import (
    add_report_args,
    cli_main,
    cli_main_from_args,
)
from .._report_models import SingleTestsValidationReport
from ..validate_tests import (
    run_validate_tests,
    ValidateTestsOptions,
)

SUBCOMMAND = "validate-tests"


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
        prog="gxwf-validate-tests",
        description="Validate a workflow-tests YAML file against the Tests schema.",
    )
    parser.add_argument("workflow_path", help="Path to a single *-tests.yml / *.gxwf-tests.yml file")
    _add_args(parser)
    return parser


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Validate a workflow-tests YAML file")
    p.add_argument("workflow_path", help="Path to a single *-tests.yml / *.gxwf-tests.yml file")
    _add_args(p)
    p.set_defaults(
        func=lambda args: cli_main_from_args(
            ValidateTestsOptions, run_validate_tests, args, SingleTestsValidationReport
        )
    )


def main(argv=None):
    cli_main(
        build_parser(),
        ValidateTestsOptions,
        run_validate_tests,
        argv,
        report_schema_model=SingleTestsValidationReport,
    )


if __name__ == "__main__":
    main()
