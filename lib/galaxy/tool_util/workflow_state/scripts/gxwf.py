"""Unified gxwf CLI entry point."""

import argparse
import sys

from . import (
    workflow_clean_stale_state,
    workflow_clean_stale_state_tree,
    workflow_convert,
    workflow_lint_stateful,
    workflow_lint_stateful_tree,
    workflow_roundtrip_validate,
    workflow_roundtrip_validate_tree,
    workflow_validate,
    workflow_validate_tests,
    workflow_validate_tests_tree,
    workflow_validate_tree,
)
from ._gxformat2_passthrough import register_passthrough

_SINGLE_FILE = [
    workflow_validate,
    workflow_validate_tests,
    workflow_clean_stale_state,
    workflow_lint_stateful,
    workflow_roundtrip_validate,
]
_TREE = [
    workflow_validate_tree,
    workflow_validate_tests_tree,
    workflow_clean_stale_state_tree,
    workflow_lint_stateful_tree,
    workflow_roundtrip_validate_tree,
]


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gxwf",
        description="Galaxy workflow CLI — validate, clean, lint, convert, and roundtrip workflows.",
    )
    sub = parser.add_subparsers(dest="subcommand", metavar="<command>")
    sub.required = True
    for mod in _SINGLE_FILE + _TREE:
        mod.register(sub)
    workflow_convert.register(sub)
    workflow_convert.register_tree(sub)
    register_passthrough(sub, "viz", "gxwf-viz", "Interactive Cytoscape graph (requires gxformat2)")
    register_passthrough(sub, "abstract-export", "gxwf-abstract-export", "Abstract CWL export (requires gxformat2)")
    register_passthrough(sub, "mermaid", "gxwf-mermaid", "Mermaid diagram (requires gxformat2)")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
