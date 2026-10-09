"""Unified gxwf CLI entry point."""

import argparse
import sys

from . import (
    workflow_clean_stale_state,
    workflow_clean_stale_state_tree,
    workflow_convert,
    workflow_lint_stateful,
    workflow_lint_stateful_tree,
    workflow_repo_search,
    workflow_roundtrip_validate,
    workflow_roundtrip_validate_tree,
    workflow_tool_revisions,
    workflow_tool_search,
    workflow_tool_versions,
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
_TOOLSHED = [
    workflow_tool_search,
    workflow_repo_search,
    workflow_tool_versions,
    workflow_tool_revisions,
]


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gxwf",
        description="Galaxy workflow CLI — validate, clean, lint, convert, and roundtrip workflows.",
    )
    sub = parser.add_subparsers(dest="subcommand", metavar="<command>")
    sub.required = True
    for mod in _SINGLE_FILE + _TREE + _TOOLSHED:
        mod.register(sub)
    workflow_convert.register(sub)
    workflow_convert.register_tree(sub)
    register_passthrough(sub, "viz", "gxformat2.cytoscape:main", "Interactive Cytoscape graph")
    register_passthrough(sub, "abstract-export", "gxformat2.abstract:main", "Abstract CWL export")
    register_passthrough(sub, "mermaid", "gxformat2.mermaid:main", "Mermaid diagram")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
