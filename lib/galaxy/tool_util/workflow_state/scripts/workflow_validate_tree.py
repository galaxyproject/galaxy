"""Thin CLI entry point for gxwf-state-validate-tree."""

from .._cli_common import (
    add_report_args,
    add_strict_args,
    build_base_parser,
    cli_main,
)
from .._report_models import TreeValidationReport
from ..validate import (
    run_validate_tree,
    ValidateTreeOptions,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-state-validate-tree",
        description="Validate all workflows under a directory tree.",
        stale_key_mode="validate",
        workflow_path_help="Path to directory containing .ga/.gxwf.yml workflows",
    )
    add_strict_args(parser)
    parser.add_argument("--summary", action="store_true", help="Show only summary counts")
    parser.add_argument("--connections", action="store_true", help="Validate inter-step connection type compatibility")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Run full stale-key cleaning before validating (for uncleaned workflows)",
    )
    parser.add_argument(
        "--mode",
        choices=["pydantic", "json-schema"],
        default="pydantic",
        help="Validation backend: pydantic (default) or json-schema",
    )
    parser.add_argument(
        "--tool-schema-dir",
        default=None,
        help="Directory of pre-exported per-tool JSON Schemas (for offline json-schema mode)",
    )
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), ValidateTreeOptions, run_validate_tree, argv, report_schema_model=TreeValidationReport)


if __name__ == "__main__":
    main()
