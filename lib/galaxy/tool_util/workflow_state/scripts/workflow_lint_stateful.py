"""Thin CLI entry point for gxwf-lint-stateful."""

from .._cli_common import (
    add_report_args,
    add_strict_args,
    build_base_parser,
    build_base_subparser_args,
    cli_main,
    cli_main_from_args,
)
from .._report_models import SingleLintReport
from ..lint_stateful import (
    LintStatefulOptions,
    run_lint_stateful,
)

SUBCOMMAND = "lint"


def _add_args(parser):
    add_strict_args(parser)
    parser.add_argument("--summary", action="store_true", help="Show only summary counts")
    parser.add_argument("--connections", action="store_true", help="Validate inter-step connection type compatibility")
    parser.add_argument(
        "--skip-best-practices",
        action="store_true",
        default=False,
        help="Skip best practice checks (annotation, creator, license, step metadata)",
    )
    parser.add_argument(
        "--training-topic",
        required=False,
        help="If this is a training workflow, specify a training topic",
    )
    add_report_args(parser)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-lint-stateful",
        description="Lint Galaxy workflows: structural checks + tool state validation.",
        stale_key_mode="validate",
    )
    _add_args(parser)
    return parser


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Lint workflows: structural checks + tool state validation")
    build_base_subparser_args(p, stale_key_mode="validate")
    _add_args(p)
    p.set_defaults(func=lambda args: cli_main_from_args(LintStatefulOptions, run_lint_stateful, args, SingleLintReport))


def main(argv=None):
    cli_main(build_parser(), LintStatefulOptions, run_lint_stateful, argv, report_schema_model=SingleLintReport)


if __name__ == "__main__":
    main()
