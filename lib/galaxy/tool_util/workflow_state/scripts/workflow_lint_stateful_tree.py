"""Thin CLI entry point for gxwf-lint-stateful-tree."""

from .._cli_common import (
    add_report_args,
    build_base_parser,
    cli_main,
)
from .._report_models import LintTreeReport
from ..lint_stateful import (
    LintStatefulTreeOptions,
    run_lint_stateful_tree,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-lint-stateful-tree",
        description="Lint all workflows in a directory: structural checks + tool state validation.",
        stale_key_mode="validate",
        workflow_path_help="Path to directory containing .ga/.gxwf.yml workflows",
    )
    parser.add_argument("--strict", action="store_true", help="Treat skips (missing tool defs) as failures")
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
    return parser


def main(argv=None):
    cli_main(build_parser(), LintStatefulTreeOptions, run_lint_stateful_tree, argv, report_schema_model=LintTreeReport)


if __name__ == "__main__":
    main()
