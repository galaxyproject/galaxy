#!/usr/bin/env python
"""Build a mulled images for a tool source (Galaxy or CWL tool).

Examples:

Build mulled images for requirements defined in a tool:

    mulled-build-tool build path/to/tool_file.xml

"""
from typing import (
    List,
    TYPE_CHECKING,
)

from galaxy.tool_util.parser import get_tool_source
from ._cli import arg_parser
from .mulled_build import (
    add_build_arguments,
    add_single_image_arguments,
    args_to_mull_targets_kwds,
    mull_targets,
    target_str_to_targets,
)

if TYPE_CHECKING:
    from galaxy.tool_util.deps.conda_util import CondaTarget


def _mulled_build_tool(tool, args):
    tool_source = get_tool_source(tool)
    requirements, *_ = tool_source.parse_requirements_and_containers()
    targets = requirements_to_mulled_targets(requirements)
    kwds = args_to_mull_targets_kwds(args)
    mull_targets(targets, **kwds)


def main(argv=None) -> None:
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    add_build_arguments(parser)
    add_single_image_arguments(parser)
    parser.add_argument("command", metavar="COMMAND", help="Command (build-and-test, build, all)")
    parser.add_argument("tool", metavar="TOOL", default=None, help="Path to tool to build mulled image for.")
    args = parser.parse_args()
    _mulled_build_tool(args.tool, args)


def requirements_to_mulled_targets(requirements) -> List["CondaTarget"]:
    """Convert Galaxy's representation of requirements into a list of CondaTarget objects.

    Only package requirements are retained.
    """
    package_requirements = [r for r in requirements if r.type == "package"]
    target_str = ",".join([f"{r.name}={r.version}" for r in package_requirements])
    targets = target_str_to_targets(target_str)
    return targets


__all__ = ("main", "requirements_to_mulled_targets")


if __name__ == "__main__":
    main()
